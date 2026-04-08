import os
from pathlib import Path

import pandas as pd

LATEST_CHECKLIST_DIR = "latest_checklist"


def load_checklist_rows_from_xlsx(path, sheet_name="checklist"):
    """
    Read the checklist sheet as a list of row dicts (column header -> value).

    Uses pandas instead of openpyxl read_only mode: some workbooks only expose a
    single column per row under read_only (merged/sparse XML), which breaks enums/classes.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Checklist Excel file not found: {path}")

    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=0, engine="openpyxl")
    except ValueError as exc:
        if "Worksheet named" in str(exc):
            raise ValueError(f"Sheet '{sheet_name}' not found in {path}") from exc
        raise

    records = []
    for _, row in df.iterrows():
        rec = {}
        for col in df.columns:
            key = str(col).strip() if col is not None else ""
            if not key:
                continue
            val = row[col]
            if pd.isna(val):
                val = None
            elif isinstance(val, str):
                val = val.strip()
            rec[key] = val
        records.append(rec)
    return records


def resolve_single_checklist_file(required_suffix=".xlsx"):
    """
    Resolve the single authoritative checklist file from latest_checklist/.

    Rules:
    - Directory must exist.
    - Exactly one file must be present.
    - File must match the required suffix (default: .xlsx).
    """
    checklist_dir = Path(LATEST_CHECKLIST_DIR)
    if not checklist_dir.exists() or not checklist_dir.is_dir():
        raise FileNotFoundError(
            f"Checklist directory not found: {checklist_dir}. "
            f"Create it and place exactly one checklist file inside."
        )

    files = [p for p in checklist_dir.iterdir() if p.is_file()]
    if len(files) != 1:
        raise ValueError(
            f"Expected exactly 1 checklist file in {checklist_dir}, found {len(files)}."
        )

    checklist_file = files[0]
    if required_suffix and checklist_file.suffix.lower() != required_suffix.lower():
        raise ValueError(
            f"Checklist file must end with '{required_suffix}', found: {checklist_file.name}"
        )
    return os.fspath(checklist_file)
