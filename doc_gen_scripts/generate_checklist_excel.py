"""Build the classic Excel checklist from schema.yaml (#147).

Run from the repository root: python doc_gen_scripts/generate_checklist_excel.py
(pip install pyyaml openpyxl pandas). Writes build/FAIRe_checklist_v<version>_classic.xlsx.

The classic checklist keeps the layout of the v1.0 checklist, because tools read terms by
row number: the same columns in the same order, and every term in the row of its v1.0
term. Each slot's v1_row annotation links to that row in the published v1.0 Excel
(sheet checklist, column C). The v1.0 Excel is downloaded once into build/ and used to
check the rows and to fill the rows of retired terms and the "v1.0 to v2.0" sheet. The
formatting (fonts, colours, empty cells, text in a shared-strings table) follows v1.0.2.

The files are dated by the last commit that changed what they are built from (the model or
these two scripts), not by the time of the build, so a rebuild gives byte-identical files
until one of those changes.
"""
import argparse
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone

import pandas as pd
import yaml
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

BUILD_DIR = "build"
# What the Excel files are built from; the last commit that changed any of them dates the files.
SOURCE_PATHS = ["slots", "enums.yaml", "classes.yaml", "types.yaml", "schema_header.yaml",
                "doc_gen_scripts/generate_checklist_excel.py", "doc_gen_scripts/generate_FULLtemplate_excel.py"]
V1_ROW_RE = re.compile(r"^(https://\S+\.xlsx)#checklist!C(\d+)$")

# v1.0.2 sets the font of every cell it writes: Calibri 11, black.
FONT = Font(name="Calibri", size=11, color="FF000000")
BOLD = Font(name="Calibri", size=11, color="FF000000", bold=True)

COLUMNS = [
    "data_type", "section", "term_name", "description", "requirement_level_code",
    "requirement_level", "requirement_level_condition", "term_type", "unit", "fixed_format",
    "controlled_vocabulary_options", "example", "sample_type_specificity", "source",
    "URI", "modifications_made"
]

requirement_specific_colors = {
    "M": "FFE26B0A", "HR": "FFFFCC00", "R": "FFFFFF99", "O": "FFCCFF99"
}

explicit_section_colors = {
    "Project": "FFFBB4AE", "Data management": "FFB3CDE3", "Sample information": "FFCCEBC5",
    "Sample relations": "FFDECBE4", "Sample collection": "FFFED9A6", "Sample storage": "FFFFFFCC",
    "Sample preparation": "FFE5D8BD", "Nucleic acid extraction": "FFFDDAEC", "PCR": "FFFBB4AE",
    "Targeted assay detection": "FFB3CDE3", "Library preparation sequencing": "FFCCEBC5",
    "Bioinformatics": "FFDECBE4", "OTU/ASV": "FFFED9A6", "Environment": "FFFFFFCC"
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


def put(ws, row, column, value, font=FONT):
    """Write a cell in v1.0.2's font. Empty values stay empty cells, as in v1.0.2."""
    cell = ws.cell(row=row, column=column, value=value if value not in ("", None) else None)
    cell.font = font
    return cell


def set_views(wb):
    """v1.0.2 sheets state zoom 100% and gridlines on."""
    for ws in wb.worksheets:
        ws.sheet_view.zoomScale = 100
        ws.sheet_view.showGridLines = True


def source_date():
    """The date of the last commit on this branch that changed SOURCE_PATHS (a merge into dev
    counts as the date of the merge). Outside a git checkout: now, with a warning."""
    try:
        out = subprocess.run(["git", "log", "-1", "--first-parent", "--format=%cI", "--", *SOURCE_PATHS],
                             capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return datetime.fromisoformat(out)
    except (OSError, subprocess.CalledProcessError):
        pass
    print("Warning: no git history; dating the Excel files now.", file=sys.stderr)
    return datetime.now().astimezone().replace(microsecond=0)


def save(wb, path, date):
    """Save with text in a shared-strings table, as Excel does (openpyxl writes it into
    each cell as an inline string). The file's properties and the zip entries carry the
    source date, so the same sources always give the same bytes."""
    utc = date.astimezone(timezone.utc).replace(tzinfo=None)
    wb.properties.created = wb.properties.modified = utc
    wb.save(path)
    with zipfile.ZipFile(path) as z:
        parts = [(info, z.read(info.filename)) for info in z.infolist()]
    strings, index, refs = [], {}, [0]

    def shared(match):
        text = match.group(3) or b""
        refs[0] += 1
        if text not in index:
            index[text] = len(strings)
            strings.append(text)
        return b"<c " + match.group(1) + b't="s"><v>' + str(index[text]).encode() + b"</v></c>"

    cell = re.compile(rb'<c ([^>]*?)t="inlineStr"\s*(/>|></c>|><is><t(?: [^>]*)?>(.*?)</t></is></c>)', re.S)
    w3c = utc.strftime("%Y-%m-%dT%H:%M:%SZ").encode()
    out = []
    for info, data in parts:
        if info.filename.startswith("xl/worksheets/sheet"):
            data = cell.sub(shared, data)
        elif info.filename == "docProps/core.xml":
            # openpyxl sets "modified" to the time of saving.
            data = re.sub(rb"(<dcterms:modified[^>]*>)[^<]*", lambda m: m.group(1) + w3c, data)
        elif info.filename == "[Content_Types].xml":
            data = data.replace(b"</Types>", b'<Override PartName="/xl/sharedStrings.xml" ContentType="application/'
                                b'vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
        elif info.filename == "xl/_rels/workbook.xml.rels":
            data = data.replace(b"</Relationships>", b'<Relationship Id="rIdSharedStrings" Type="http://schemas.'
                                b'openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
                                b'Target="sharedStrings.xml"/></Relationships>')
        out.append((info, data))
    items = b"".join(b"<si><t" + (b' xml:space="preserve"' if t != t.strip() or b"\n" in t else b"") + b">" + t
                     + b"</t></si>" for t in strings)
    sst = (b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<sst xmlns="http://schemas.openxmlformats.org/'
           b'spreadsheetml/2006/main" count="%d" uniqueCount="%d">' % (refs[0], len(strings))
           + items + b"</sst>")
    stamp = utc.timetuple()[:6]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in [(info.filename, data) for info, data in out] + [("xl/sharedStrings.xml", sst)]:
            z.writestr(zipfile.ZipInfo(name, date_time=stamp), data, compress_type=zipfile.ZIP_DEFLATED)


def write_workbook(rows, changes, glossary, v1_url, path, date):
    wb = Workbook()
    ws_readme = wb.active
    ws_readme.title = "README"
    put(ws_readme, 1, 1, "Instructions for data submitters:", BOLD)
    for i, line in enumerate(instructions, start=2):
        put(ws_readme, i, 2, line)
    start_row = len(instructions) + 3
    put(ws_readme, start_row, 1, "Terms and definitions:", BOLD)
    put(ws_readme, start_row + 1, 2, "Term")
    put(ws_readme, start_row + 1, 3, "Definition")
    for i, (term, definition) in enumerate(glossary.items(), start=start_row + 2):
        put(ws_readme, i, 2, str(term))
        put(ws_readme, i, 3, str(definition))

    ws = wb.create_sheet("checklist")
    for col_num, col_name in enumerate(COLUMNS, start=1):
        put(ws, 1, col_num, col_name, BOLD)
    for row_idx, record in enumerate(rows, start=2):
        section, code = record["section"], record["requirement_level_code"]
        for col_idx, col_name in enumerate(COLUMNS, start=1):
            value = record[col_name]
            cell = put(ws, row_idx, col_idx, str(value) if value else None,
                       BOLD if col_name == "term_name" else FONT)
            color = None
            if col_name == "section":
                color = explicit_section_colors.get(section)
            elif col_name in ("requirement_level_code", "requirement_level"):
                color = requirement_specific_colors.get(code)
            if color:
                cell.fill = PatternFill(start_color=color, end_color=color, fill_type="solid")

    ws_changes = wb.create_sheet("v1.0 to v2.0")
    put(ws_changes, 1, 1, f"Rows whose term changed since the v1.0 checklist ({v1_url}). "
                          "Every other row has the same term name as in v1.0.")
    header = ["row", "v1.0 term_name", "term_name", "change"]
    for col_num, col_name in enumerate(header, start=1):
        put(ws_changes, 3, col_num, col_name, BOLD)
    for i, change in enumerate(changes, start=4):
        for col_num, value in enumerate(change, start=1):
            put(ws_changes, i, col_num, value)

    set_views(wb)
    save(wb, path, date)


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
    write_workbook(rows, changes, glossary, v1_url, path, source_date())
    print(f"Excel file written: {path} ({len(rows)} rows, {len(changes)} changed since v1.0)")


if __name__ == "__main__":
    main()
