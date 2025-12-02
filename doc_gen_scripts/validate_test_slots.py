import csv
import re
from datetime import datetime
from pathlib import Path

import yaml


"""
Minimal validator for the new *_TEST slots against real CSV exports.

Usage (from repo root, in your terminal):

    python doc_gen_scripts/validate_test_slots.py input/projectMetadata.csv input/sampleMetadata.csv

This script:
  - loads constraints for *_TEST slots from schema.yaml (range, required, pattern/structured_pattern, enum_values)
  - validates:
      * project_id_TEST, mod_date_TEST, neg_cont_0_1_TEST, assay_type_TEST, accessRights_TEST
        in projectMetadata.csv (using the project_level column)
      * samp_name_TEST, env_broad_scale_TEST, sample_depth_TEST
        in sampleMetadata.csv (normal wide format, skipping sample_derived_from which is empty)
"""


PROJECT_SLOTS = [
    "project_id_TEST",
    "mod_date_TEST",
    "neg_cont_0_1_TEST",
    "assay_type_TEST",
    "accessRights_TEST",
]

SAMPLE_SLOTS = [
    "samp_name_TEST",
    "env_broad_scale_TEST",
    "sample_depth_TEST",  # will be silently skipped if column not present
]


def load_slot_constraints(schema_path: Path):
    """Load slot definitions for the *_TEST slots from schema.yaml."""
    with schema_path.open("r", encoding="utf-8") as f:
        schema = yaml.safe_load(f)

    slots = schema.get("slots", {})
    constraints = {}

    for slot_name in PROJECT_SLOTS + SAMPLE_SLOTS:
        if slot_name not in slots:
            # Slot not in schema (e.g., sample_depth_TEST not yet merged) – skip for now.
            continue
        s = slots[slot_name]
        c = {
            "name": slot_name,
            "range": s.get("range", "string"),
            "required": bool(s.get("required", False)),
            "enum_values": list((s.get("enum_values") or {}).keys()),
            "pattern": s.get("pattern"),
        }
        # structured_pattern takes precedence over plain pattern if present
        sp = s.get("structured_pattern")
        if isinstance(sp, dict) and "syntax" in sp:
            c["pattern"] = sp["syntax"]
        constraints[slot_name] = c

    return constraints


def validate_value(slot_c, raw_value):
    """Validate a single value against one slot's constraints. Return list of error messages."""
    errors = []
    value = (raw_value or "").strip()
    name = slot_c["name"]
    required = slot_c["required"]
    rng = slot_c["range"]
    pattern = slot_c.get("pattern")
    enum_vals = slot_c.get("enum_values") or []

    # Required check
    if required and value == "":
        errors.append(f"{name}: missing required value")
        # If it's required and missing, no point in further checks.
        return errors

    # Empty but not required → no more checks.
    if value == "":
        return errors

    # Enum check
    if enum_vals:
        if value not in enum_vals:
            errors.append(f"{name}: value '{value}' not in enum {enum_vals}")

    # Range-specific checks
    if rng == "boolean":
        # Accept only the canonical true/false for now; this will flag '0'/'1' if still present.
        if value.lower() not in {"true", "false"}:
            errors.append(f"{name}: expected boolean ('true'/'false'), got '{value}'")

    elif rng == "integer":
        try:
            int(value)
        except ValueError:
            errors.append(f"{name}: expected integer, got '{value}'")

    elif rng == "float":
        try:
            float(value)
        except ValueError:
            errors.append(f"{name}: expected float, got '{value}'")

    elif rng == "date":
        # Expect ISO date yyyy-mm-dd
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            errors.append(f"{name}: expected ISO date yyyy-mm-dd, got '{value}'")

    # Pattern / structured_pattern
    if pattern:
        if not re.match(pattern, value):
            errors.append(f"{name}: value '{value}' does not match pattern {pattern}")

    return errors


def validate_project_metadata(csv_path: Path, slot_constraints):
    """Validate *_TEST project slots using projectMetadata.csv."""
    errors = []
    # CSVs exported from Excel on Windows are typically in cp1252; use that and
    # replace any characters that can't be decoded so validation still runs.
    with csv_path.open(newline="", encoding="cp1252", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term_name = (row.get("term_name") or "").strip()
            if term_name not in PROJECT_SLOTS:
                continue
            slot_c = slot_constraints.get(term_name)
            if not slot_c:
                continue
            value = row.get("project_level", "")
            slot_errors = validate_value(slot_c, value)
            for e in slot_errors:
                errors.append(f"projectMetadata: term_name={term_name!r} -> {e}")
    return errors


def validate_sample_metadata(csv_path: Path, slot_constraints):
    """Validate *_TEST sample slots using sampleMetadata.csv."""
    errors = []
    with csv_path.open(newline="", encoding="cp1252", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < 3:
        return ["sampleMetadata: file has fewer than 3 rows; cannot read headers"]

    header_row = rows[2]  # row index 2 = third row (field names)
    fieldnames = header_row

    # Map of field name -> column index, for faster lookups
    col_index = {name: i for i, name in enumerate(fieldnames)}

    # Only validate slots that both (a) we have constraints for and (b) are present as columns.
    active_sample_slots = [
        s for s in SAMPLE_SLOTS if s in slot_constraints and s in col_index
    ]

    for data_row in rows[3:]:
        if not data_row:
            continue
        # Use samp_name_TEST (if present) as a row identifier for messages.
        samp_id = ""
        if "samp_name_TEST" in col_index and len(data_row) > col_index["samp_name_TEST"]:
            samp_id = data_row[col_index["samp_name_TEST"]].strip()

        for slot_name in active_sample_slots:
            slot_c = slot_constraints.get(slot_name)
            idx = col_index[slot_name]
            value = data_row[idx] if idx < len(data_row) else ""
            slot_errors = validate_value(slot_c, value)
            for e in slot_errors:
                prefix = f"sampleMetadata: samp_name_TEST={samp_id!r}, slot={slot_name!r}"
                errors.append(f"{prefix} -> {e}")

    return errors


def main():
    import sys

    if len(sys.argv) != 3:
        print(
            "Usage: python doc_gen_scripts/validate_test_slots.py "
            "input/projectMetadata.csv input/sampleMetadata.csv"
        )
        sys.exit(1)

    project_csv = Path(sys.argv[1])
    sample_csv = Path(sys.argv[2])
    schema_path = Path("schema.yaml")

    if not schema_path.exists():
        print("schema.yaml not found. Run merge_slots.py first.")
        sys.exit(1)

    slot_constraints = load_slot_constraints(schema_path)

    all_errors = []
    all_errors.extend(validate_project_metadata(project_csv, slot_constraints))
    all_errors.extend(validate_sample_metadata(sample_csv, slot_constraints))

    if not all_errors:
        print("✅ No validation errors for *_TEST slots.")
    else:
        print("❌ Validation errors for *_TEST slots:")
        for e in all_errors:
            print(" -", e)


if __name__ == "__main__":
    main()


