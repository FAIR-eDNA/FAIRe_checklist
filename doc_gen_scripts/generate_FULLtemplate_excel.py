"""Build the classic Excel full template from schema.yaml (#147).

Run from the repository root: python doc_gen_scripts/generate_FULLtemplate_excel.py
(pip install pyyaml openpyxl pandas). Writes build/FAIRe_checklist_v<version>_FULLtemplate_classic.xlsx.

The classic template keeps the layout of the v1.0 template: the same tabs, the rows of
projectMetadata and the columns of the data tabs in the v1.0 checklist's row order
(each term at its v1_row; retired terms keep their row in projectMetadata), and the
"Drop-down values" sheet with the v1.0 terms first, in v1.0 order, then the terms that
gained a controlled vocabulary since. As in v1.0, every term with a row in "Drop-down values"
has an in-cell drop-down of that row's values (other values can still be typed), and the
notes on the term names have bold labels, with Mandatory and the value list in red.
"""
import argparse
import os

import yaml
from openpyxl import Workbook
from openpyxl.cell.text import InlineFont, RichText
from openpyxl.comments import Comment
from openpyxl.comments.comment_sheet import CommentRecord
from openpyxl.styles import PatternFill
from openpyxl.styles.colors import Color
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from generate_checklist_excel import BOLD, BUILD_DIR, FONT, build_rows, put, save, set_views, source_date

level_colors = {"M": "FFE26B0A", "HR": "FFFFCC00", "R": "FFFFFF99", "O": "FFCCFF99"}
level_names = {"M": "Mandatory", "HR": "Highly recommended", "R": "Recommended", "O": "Optional"}

# Tabs after projectMetadata, and the term in column A (row 3) of each.
DATA_TABS = {
    "sampleMetadata": "samp_name",
    "ampData": "samp_name",
    "stdData": "samp_name",
    "eLowQuantData": "assay_name",
    "experimentRunMetadata": "samp_name",
    "taxaRaw": "seq_id",
    "taxaFinal": "seq_id",
}
TAB_ORDER = ["README", "projectMetadata", "Drop-down values", "sampleMetadata", "ampData", "stdData",
             "eLowQuantData", "experimentRunMetadata", "taxaRaw", "taxaFinal"]
DROPDOWN_TYPES = ("controlled vocabulary", "Boolean")
DATA_ROWS = "4:103"  # the rows of the data tabs that have drop-downs, as in v1.0
RED = "FFFF0000"
# Note boxes larger than v1.0's (147 x 96 pt), so more of the text shows: 4.5 times as wide and
# 1.5 times as tall, 661.5 x 144 pt. openpyxl takes the size in pixels.
NOTE_SIZE = {"width": 882, "height": 192}


class RichComment(Comment):
    """A note made of (text, bold, colour) runs. openpyxl writes notes as plain text only."""

    def __init__(self, runs, author):
        super().__init__("".join(text for text, _, _ in runs), author, **NOTE_SIZE)
        self.runs = runs


_from_cell = CommentRecord.from_cell.__func__


def _rich_from_cell(cls, cell):
    record = _from_cell(cls, cell)
    runs = getattr(cell._comment, "runs", None)
    if runs:
        record.text.t = None
        record.text.r = [RichText(rPr=InlineFont(rFont="Calibri", sz=11, color=Color(rgb=color), b=bold or None),
                                  t=text) for text, bold, color in runs]
    return record


CommentRecord.from_cell = classmethod(_rich_from_cell)


def fill(color):
    return PatternFill(start_color=color, end_color=color, fill_type="solid")


def tables(record):
    return [t.strip() for t in record["data_type"].split("|") if t.strip()]


def comment(record, tab):
    """The note on a term's cell, in the v1.0 template's wording and formatting: bold labels;
    a Mandatory level and a field type with its values or format in bold red / red."""
    if not record["requirement_level_code"]:
        return Comment(record["description"], "FAIRe", **NOTE_SIZE)
    level = record["requirement_level"]
    if record["requirement_level_condition"]:
        level += f" ({record['requirement_level_condition']})"
    field_type = record["term_type"]
    detail = {"controlled vocabulary": record["controlled_vocabulary_options"],
              "fixed format": record["fixed_format"] or "NA"}.get(field_type)
    if detail:
        field_type += f" ({detail})"
    mandatory = record["requirement_level"] == "Mandatory"
    fields = [("Requirement level : ", level, mandatory, RED if mandatory else "FF000000"),
              ("Description : ", record["description"], False, "FF000000"),
              ("Example : ", record["example"].split(" | ")[0] if record["example"] else "", False, "FF000000"),
              ("Field type : ", field_type, False, RED if detail else "FF000000")]
    if tab == "sampleMetadata" and record["sample_type_specificity"]:
        fields.append(("Sample type(s) : ", record["sample_type_specificity"], False, "FF000000"))
    runs = []
    for i, (label, value, bold, color) in enumerate(fields):
        last = i == len(fields) - 1 and tab == "sampleMetadata" and record["sample_type_specificity"]
        end = "" if last else "\n"
        if value.strip():
            runs += [(label, True, "FF000000"), (value + end, bold, color)]
        else:
            # Excel reports the file as damaged if a run holds only a line break (an empty example).
            runs.append((label + end, True, "FF000000"))
    return RichComment(runs, "FAIRe")


def write_readme(ws, version, date):
    """date: when the sources last changed (see source_date), not the time of the build."""
    lines = ["The templates were generated using the FAIR eDNA checklist version of;",
             f"FAIRe_checklist_v{version}", "", "Date/Time generated;",
             date.isoformat(timespec="seconds"), "",
             "Note: This template includes all data components and terms from the FAIR eDNA checklist, "
             "encompassing sections for both targeted assays and metabarcoding assay types.", "",
             "Requirement levels;"]
    for row, line in enumerate(lines, start=1):
        # v1.0.2 has empty text, not empty cells, in rows 3, 6 and 8.
        ws.cell(row=row, column=1, value=line).font = FONT
    for row, code in enumerate(level_colors, start=10):
        put(ws, row, 1, f"{code} = {level_names[code]}").fill = fill(level_colors[code])


def dropdown(ws, dropdowns, term, cells, absolute):
    """An in-cell drop-down of the term's values in "Drop-down values", as in v1.0."""
    if term not in dropdowns:
        return
    row, n = dropdowns[term]
    last = get_column_letter(4 + n)
    source = (f"'Drop-down values'!$E${row}:${last}${row}" if absolute
              else f"'Drop-down values'!E{row}:{last}{row}")
    dv = DataValidation(type="list", formula1=source, allow_blank=True, showInputMessage=True,
                        showErrorMessage=False)
    dv.add(cells)
    ws.add_data_validation(dv)


def write_project_tab(ws, rows, dropdowns):
    for col, name in enumerate(["requirement_level_code", "section", "term_name", "project_level"], start=1):
        put(ws, 1, col, name, BOLD)
    row = 1
    for record in rows:
        if "projectMetadata" not in tables(record):
            continue
        row += 1
        code = record["requirement_level_code"]
        put(ws, row, 1, code)
        put(ws, row, 2, record["section"])
        put(ws, row, 3, record["term_name"], BOLD).comment = comment(record, "projectMetadata")
        if code in level_colors:
            ws.cell(row=row, column=1).fill = fill(level_colors[code])
        dropdown(ws, dropdowns, record["term_name"], f"D{row}", absolute=False)


def write_data_tab(ws, tab, first_term, rows, dropdowns):
    columns = [r for r in rows if tab in tables(r) and r["term_name"] != first_term]
    put(ws, 1, 1, "# requirement_level_code")
    put(ws, 2, 1, "# section")
    put(ws, 3, 1, first_term, BOLD)
    for col, record in enumerate(columns, start=2):
        letter = get_column_letter(col)
        code = record["requirement_level_code"]
        put(ws, 1, col, code)
        put(ws, 2, col, record["section"])
        put(ws, 3, col, record["term_name"], BOLD).comment = comment(record, tab)
        if code in level_colors:
            ws[f"{letter}1"].fill = fill(level_colors[code])
        first, last = DATA_ROWS.split(":")
        dropdown(ws, dropdowns, record["term_name"], f"{letter}{first}:{letter}{last}", absolute=True)


def write_dropdowns(ws, rows, v1_types):
    """v1.0's drop-down terms first, in v1.0 order, then the ones added since. Returns each
    term's row and number of values."""
    entries = [(row, r) for row, r in enumerate(rows, start=2) if r["term_type"] in DROPDOWN_TYPES]
    entries.sort(key=lambda e: (v1_types.get(e[0]) not in DROPDOWN_TYPES, e[0]))
    options = [[v.strip() for v in r["controlled_vocabulary_options"].split("|")] for _, r in entries]
    width = max(len(o) for o in options)
    header = ["term_name", "term_type", "vocab_options", "n_options"] + [f"vocab{i + 1}" for i in range(width)]
    for col, name in enumerate(header, start=1):
        put(ws, 1, col, name)
    dropdowns = {}
    for row, ((_, record), opts) in enumerate(zip(entries, options), start=2):
        values = [record["term_name"], record["term_type"], record["controlled_vocabulary_options"], len(opts)] + opts
        for col, value in enumerate(values, start=1):
            put(ws, row, col, value)
        dropdowns[record["term_name"]] = (row, len(opts))
    return dropdowns


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--schema", default="schema.yaml")
    parser.add_argument("--out-dir", default=BUILD_DIR)
    args = parser.parse_args()

    with open(args.schema, "r", encoding="utf-8") as handle:
        schema = yaml.safe_load(handle)
    rows, _, _, v1 = build_rows(schema)
    v1_types = {row: v1[row]["term_type"] for row in v1}

    date = source_date()
    wb = Workbook()
    wb.active.title = "README"
    write_readme(wb["README"], schema["version"], date)
    dropdowns = write_dropdowns(wb.create_sheet("Drop-down values"), rows, v1_types)
    write_project_tab(wb.create_sheet("projectMetadata"), rows, dropdowns)
    for tab, first_term in DATA_TABS.items():
        write_data_tab(wb.create_sheet(tab), tab, first_term, rows, dropdowns)
    wb._sheets.sort(key=lambda ws: TAB_ORDER.index(ws.title))
    set_views(wb)

    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"FAIRe_checklist_v{schema['version']}_FULLtemplate_classic.xlsx")
    save(wb, path, date)
    print(f"Excel file written: {path}")


if __name__ == "__main__":
    main()
