import os
from pathlib import Path


LATEST_CHECKLIST_DIR = "latest_checklist"


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
