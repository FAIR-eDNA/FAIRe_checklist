"""Build the classic Excel checklist from schema.yaml (#147).

Run from the repository root: python doc_gen_scripts/generate_checklist_excel.py
(pip install pyyaml openpyxl pandas). Writes build/FAIRe_checklist_v<version>_classic.xlsx.

The classic checklist keeps the layout of the v1.0 checklist, because tools read terms by
row number: the same columns in the same order, and every term in the row of its v1.0
term. Each slot's v1_row annotation links to that row in the published v1.0 Excel
(sheet checklist, column C). The v1.0 Excel is downloaded once into build/ and used to
check the rows and to fill the rows of retired terms and the "v1.0 to v2.0" sheet.
"""
import argparse
import os
import re
import urllib.request

import pandas as pd
import yaml
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

BUILD_DIR = "build"
V1_ROW_RE = re.compile(r"^(https://\S+\.xlsx)#checklist!C(\d+)$")

COLUMNS = [
    "data_type", "section", "term_name", "description", "requirement_level_code",
    "requirement_level", "requirement_level_condition", "term_type", "unit", "fixed_format",
    "controlled_vocabulary_options", "example", "sample_type_specificity", "source",
    "URI", "modifications_made"
]

requirement_specific_colors = {
    "M": "FFE26B0A", "HR": "FFFFCC00", "R": "FFFDFD96", "O": "FFCCFF99"
}

explicit_section_colors = {
    "Project": "FFFBB4AE", "Data management": "FFB3CDE3", "Sample information": "FFCCEBC5",
    "Sample relations": "FFDECBE4", "Sample collection": "FFFED9A6", "Sample storage": "FFFFFFCC",
    "Sample preparation": "FFE5D8BD", "Nucleic acid extraction": "FFFDDAEC", "PCR": "FFFBB4AE",
    "Targeted assay detection": "FFB3CDE3", "Library preparation sequencing": "FFCCEBC5",
    "Bioinformatics": "FFDECBE4", "OTU/ASV": "FFFED9A6", "Environment": "FFFFFF99"
}

instructions = [
    'Date and time must be recorded following ISO 8601 format (yyyy-mm-ddThh:mm:ss). Time zone must be specified after the timestamp e.g., "2008-01-23T19:23-06:00" in the time zone six hours earlier than UTC, or "2008-01-23T19:23Z" at UTC time. In Excel, format the cell as text to prevent from automatic conversion to other date fromats.',
    "Time duration must be recorded following ISO 8601 durations (PnYnMnWnDTnHnMnS for P<date>T<time>). e.g., P1Y1M1DT1H1M1.1S = One year, one month, one day, one hour, one minute, one second, and 100 milliseconds",
    "A date and time range can be specified using a forward slash (/) to separate the start and end values (e.g., 2008-01-23T19:23-06:00/2008-01-23T19:53-06:00).",
    "Use space vertical bar space ( | ) to separate multiple values in a list. i.e., x | y | z",
    "Use hyphen (-) to indicate a range of numeric or integer values. In Excel, format the cell as text to prevent it from being auto-formatted as a date.",
    "For numeric fields, enter only numbers and do not enter units. Read the descriptions for the standard unit.",
    "For Boolean type of questions, always read the descriptions and answer with 0 or 1.",
    'When "other" is selected in a controlled vocabulary term, write the answer using the format of "other: FREE TEXT DESCRIPTION".',
    "If suitable term names are not available in the current checklist, users should search for them in existing standards, such as MIxS (https://genomicsstandardsconsortium.github.io/mixs/) and DwC (https://dwc.tdwg.org/terms/), and use these standardized terms where possible. If relevant terms cannot be found in these resources, users may add new terms using clear, concise, and descriptive names within related tables.",
    "When a value is missing from a mandatory term, it is required to provide the reason using the INSDC missing value controlled vocabulary (https://www.insdc.org/submitting-standards/missing-value-reporting/). See https://fair-edna.github.io/guidelines.html#missing-values for the full list of values."
]


def v1_row(slot_name, slot):
    """The (v1.0 Excel URL, row) a slot's v1_row annotation points to."""
    link = str((slot.get("annotations") or {}).get("v1_row") or "")
    match = V1_ROW_RE.match(link)
    if not match:
        raise ValueError(f"{slot_name}: v1_row annotation missing or not a link to a cell in "
                         f"column C of the v1.0 checklist: {link!r}")
    return match.group(1), int(match.group(2))


def load_v1(url):
    """The v1.0 checklist sheet, keyed by Excel row number."""
    os.makedirs(BUILD_DIR, exist_ok=True)
    path = os.path.join(BUILD_DIR, "v1.0_" + url.rsplit("/", 1)[1])
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    df = pd.read_excel(path, sheet_name="checklist", dtype=str).fillna("")
    return {i + 2: row for i, row in enumerate(df.to_dict("records"))}


def expand(curie, prefixes):
    """A CURIE as a full URI, the way the v1.0 checklist wrote URIs."""
    if not curie:
        return ""
    prefix, _, local = str(curie).partition(":")
    return prefixes[prefix] + local if prefix in prefixes and local else str(curie)


def ranges(slot):
    any_of = slot.get("any_of") or []
    return [x.get("range") for x in any_of] if any_of else [slot.get("range")]


def pattern(slot, types):
    """The slot's own pattern, else the pattern of its type (e.g. Timestamp, EnvoTerm)."""
    if slot.get("pattern"):
        return slot["pattern"]
    return (types.get(slot.get("range")) or {}).get("pattern", "")


def term_type(slot, enums, types):
    rs = ranges(slot)
    if "BooleanEnum" in rs:
        return "Boolean"
    has_enum = any(r in enums for r in rs)
    if has_enum and ("float" in rs or "integer" in rs):
        return "numeric or controlled vocabulary"
    if has_enum:
        return "controlled vocabulary"
    if "float" in rs:
        return "numeric"
    if "integer" in rs:
        return "integer"
    if pattern(slot, types):
        return "fixed format"
    return "free text"


def vocabulary(slot, enums):
    rs = ranges(slot)
    if "BooleanEnum" in rs:
        return "0 | 1"
    values = []
    for r in rs:
        if r in enums:
            values.extend(str(v) for v in (enums[r].get("permissible_values") or {}))
    if values and ("float" in rs or "integer" in rs):
        values.insert(0, "numeric value")
    if values and "OtherText" in rs:
        values.append("other:")
    return " | ".join(values)


def examples(slot):
    values = []
    for item in slot.get("examples") or []:
        value = item.get("value", "") if isinstance(item, dict) else item
        if isinstance(value, list):
            value = " | ".join(str(v) for v in value)
        if value not in ("", None):
            values.append(str(value))
    return " | ".join(values)


def unit(slot):
    u = slot.get("unit")
    if isinstance(u, dict):
        return u.get("descriptive_name") or u.get("ucum_code") or ""
    return str(u or "")


def slot_record(name, slot, enums, types, prefixes):
    ann = slot.get("annotations") or {}
    subsets = slot.get("in_subset") or []
    return {
        "data_type": ann.get("data_type", ""),
        "section": " | ".join(subsets) if isinstance(subsets, list) else str(subsets),
        "term_name": name,
        "description": slot.get("description", ""),
        "requirement_level_code": ann.get("requirement_level_code", ""),
        "requirement_level": ann.get("requirement_level", ""),
        "requirement_level_condition": ann.get("requirement_level_condition", ""),
        "term_type": term_type(slot, enums, types),
        "unit": unit(slot),
        "fixed_format": pattern(slot, types) if term_type(slot, enums, types) == "fixed format" else "",
        "controlled_vocabulary_options": vocabulary(slot, enums),
        "example": examples(slot),
        "sample_type_specificity": ann.get("sample_type_specificity", ""),
        "source": expand(slot.get("source"), prefixes),
        "URI": expand(slot.get("slot_uri"), prefixes),
        "modifications_made": ann.get("modifications_made", ""),
    }


def build_rows(schema):
    """Checklist rows in v1.0 row order, the v1.0 -> v2.0 changes, and the v1.0 URL and rows."""
    slots, enums, prefixes = schema["slots"], schema.get("enums") or {}, schema["prefixes"]
    types = schema.get("types") or {}
    url, by_row = None, {}
    for name, slot in slots.items():
        slot_url, row = v1_row(name, slot)
        if url and slot_url != url:
            raise ValueError(f"{name}: v1_row links to {slot_url}, other slots to {url}")
        url = slot_url
        if row in by_row:
            raise ValueError(f"{name} and {by_row[row]} both have v1.0 row {row}")
        by_row[row] = name
    v1 = load_v1(url)
    renamed_to = {}
    for name, slot in slots.items():
        for alias in slot.get("aliases") or []:
            renamed_to.setdefault(alias, []).append(name)

    rows, changes = [], []
    for row in sorted(v1):
        old = v1[row]["term_name"]
        name = by_row.get(row)
        if name:
            rows.append(slot_record(name, slots[name], enums, types, prefixes))
            if name != old:
                aliases = slots[name].get("aliases") or []
                if old in aliases and len(aliases) > 1:
                    change = f"merged: replaces {' and '.join(aliases)}"
                elif old in aliases:
                    change = "renamed"
                else:
                    change = "different term name in this row; read the descriptions"
                changes.append([row, old, name, change])
        else:
            successors = renamed_to.get(old)
            if not successors:
                raise ValueError(f"v1.0 row {row} ({old}) has no slot, and no slot has {old} in aliases")
            note = (f"Retired in FAIRe v{schema['version']}: merged into "
                    f"{' | '.join(successors)}. This row is kept empty so that later rows keep their v1.0 row numbers.")
            rows.append({**{c: "" for c in COLUMNS}, "data_type": v1[row]["data_type"],
                         "section": v1[row]["section"], "term_name": old, "description": note})
            changes.append([row, old, "", f"retired; merged into {' | '.join(successors)}"])
    extra = sorted(set(by_row) - set(v1))
    if extra:
        raise ValueError(f"v1_row beyond the v1.0 checklist: rows {extra}")
    return rows, changes, url, v1


def write_workbook(rows, changes, glossary, v1_url, path):
    wb = Workbook()
    bold = Font(bold=True)
    ws_readme = wb.active
    ws_readme.title = "README"
    ws_readme.cell(row=1, column=1, value="Instructions for data submitters:").font = bold
    for i, line in enumerate(instructions, start=2):
        ws_readme.cell(row=i, column=2, value=line)
    start_row = len(instructions) + 3
    ws_readme.cell(row=start_row, column=1, value="Terms and definitions:").font = bold
    ws_readme.cell(row=start_row + 1, column=2, value="Term").font = bold
    ws_readme.cell(row=start_row + 1, column=3, value="Definition").font = bold
    for i, (term, definition) in enumerate(glossary.items(), start=start_row + 2):
        ws_readme.cell(row=i, column=2, value=str(term))
        ws_readme.cell(row=i, column=3, value=str(definition))

    ws = wb.create_sheet("checklist")
    for col_num, col_name in enumerate(COLUMNS, start=1):
        ws.cell(row=1, column=col_num, value=col_name).font = bold
    for row_idx, record in enumerate(rows, start=2):
        section, code = record["section"], record["requirement_level_code"]
        for col_idx, col_name in enumerate(COLUMNS, start=1):
            value = record[col_name]
            cell = ws.cell(row=row_idx, column=col_idx, value=str(value) if value else "")
            color = None
            if col_name == "section":
                color = explicit_section_colors.get(section)
            elif col_name in ("requirement_level_code", "requirement_level"):
                color = requirement_specific_colors.get(code)
            if color:
                cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

    ws_changes = wb.create_sheet("v1.0 to v2.0")
    ws_changes.cell(row=1, column=1, value=f"Rows whose term changed since the v1.0 checklist ({v1_url}). "
                                           "Every other row has the same term name as in v1.0.")
    header = ["row", "v1.0 term_name", "term_name", "change"]
    for col_num, col_name in enumerate(header, start=1):
        ws_changes.cell(row=3, column=col_num, value=col_name).font = bold
    for i, change in enumerate(changes, start=4):
        for col_num, value in enumerate(change, start=1):
            ws_changes.cell(row=i, column=col_num, value=value)

    wb.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--schema", default="schema.yaml")
    parser.add_argument("--out-dir", default=BUILD_DIR)
    args = parser.parse_args()

    with open(args.schema, "r", encoding="utf-8") as handle:
        schema = yaml.safe_load(handle)
    with open("slots/glossary_annotation.yaml", "r", encoding="utf-8") as handle:
        glossary = yaml.safe_load(handle)["annotations"]["glossary"]

    rows, changes, v1_url, _ = build_rows(schema)
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"FAIRe_checklist_v{schema['version']}_classic.xlsx")
    write_workbook(rows, changes, glossary, v1_url, path)
    print(f"Excel file written: {path} ({len(rows)} rows, {len(changes)} changed since v1.0)")


if __name__ == "__main__":
    main()
