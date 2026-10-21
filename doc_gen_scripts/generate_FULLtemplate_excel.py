"""Build the classic Excel full template from schema.yaml (#147).

Run from the repository root: python doc_gen_scripts/generate_FULLtemplate_excel.py
(pip install pyyaml openpyxl pandas). Writes build/FAIRe_checklist_v<version>_FULLtemplate_classic.xlsx.

The classic template keeps the layout of the v1.0 template: the same tabs, the rows of
projectMetadata and the columns of the data tabs in the v1.0 checklist's row order
(each term at its v1_row; retired terms keep their row in projectMetadata), and the
"Drop-down values" sheet with the v1.0 terms first, in v1.0 order, then the terms that
gained a controlled vocabulary since. Like v1.0, it has no in-cell drop-downs.
"""
import argparse
import os
from datetime import datetime

import yaml
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from generate_checklist_excel import BUILD_DIR, build_rows

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


def fill(color):
    return PatternFill(start_color=color, end_color=color, fill_type="solid")


def tables(record):
    return [t.strip() for t in record["data_type"].split("|") if t.strip()]


def comment_text(record, tab):
    """The note on a term's cell, in the v1.0 template's wording."""
    if not record["requirement_level_code"]:
        return record["description"]
    field_type = record["term_type"]
    detail = record["fixed_format"] or record["controlled_vocabulary_options"]
    if detail and field_type != "Boolean":
        field_type += f" ({detail})"
    lines = [f"Requirement level : {record['requirement_level']}",
             f"Description : {record['description']}",
             f"Example : {record['example'].split(' | ')[0] if record['example'] else ''}",
             f"Field type : {field_type}"]
    if tab == "sampleMetadata" and record["sample_type_specificity"]:
        lines.append(f"Sample type(s) : {record['sample_type_specificity']}")
    return "\n".join(lines) + ("" if tab == "sampleMetadata" and record["sample_type_specificity"] else "\n")


def write_readme(ws, version):
    ws["A1"] = "The templates were generated using the FAIR eDNA checklist version of;"
    ws["A2"] = f"FAIRe_checklist_v{version}"
    ws["A4"] = "Date/Time generated;"
    ws["A5"] = datetime.now().astimezone().isoformat(timespec="seconds")
    ws["A7"] = ("Note: This template includes all data components and terms from the FAIR eDNA checklist, "
                "encompassing sections for both targeted assays and metabarcoding assay types.")
    ws["A9"] = "Requirement levels;"
    for row, code in enumerate(level_colors, start=10):
        ws[f"A{row}"] = f"{code} = {level_names[code]}"
        ws[f"A{row}"].fill = fill(level_colors[code])


def write_project_tab(ws, rows):
    bold = Font(bold=True)
    ws.append(["requirement_level_code", "section", "term_name", "project_level"])
    for col in range(1, 5):
        ws.cell(row=1, column=col).font = bold
    for record in rows:
        if "projectMetadata" not in tables(record):
            continue
        code = record["requirement_level_code"]
        ws.append([code, record["section"], record["term_name"], None])
        cell = ws.cell(row=ws.max_row, column=3)
        cell.font = bold
        cell.comment = Comment(comment_text(record, "projectMetadata"), "FAIRe")
        if code in level_colors:
            ws.cell(row=ws.max_row, column=1).fill = fill(level_colors[code])


def write_data_tab(ws, tab, first_term, rows):
    bold = Font(bold=True)
    columns = [r for r in rows if tab in tables(r) and r["term_name"] != first_term]
    ws.append(["# requirement_level_code"] + [r["requirement_level_code"] for r in columns])
    ws.append(["# section"] + [r["section"] for r in columns])
    ws.append([first_term] + [r["term_name"] for r in columns])
    for col, record in enumerate(columns, start=2):
        letter = get_column_letter(col)
        code = record["requirement_level_code"]
        if code in level_colors:
            for row in (1, 2, 3):
                ws[f"{letter}{row}"].fill = fill(level_colors[code])
        ws[f"{letter}3"].font = bold
        ws[f"{letter}3"].comment = Comment(comment_text(record, tab), "FAIRe")


def write_dropdowns(ws, rows, v1_types):
    """v1.0's drop-down terms first, in v1.0 order, then the ones added since."""
    bold = Font(bold=True)
    entries = [(row, r) for row, r in enumerate(rows, start=2) if r["term_type"] in DROPDOWN_TYPES]
    entries.sort(key=lambda e: (v1_types.get(e[0]) not in DROPDOWN_TYPES, e[0]))
    options = [[v.strip() for v in r["controlled_vocabulary_options"].split("|")] for _, r in entries]
    width = max(len(o) for o in options)
    ws.append(["term_name", "term_type", "vocab_options", "n_options"] + [f"vocab{i + 1}" for i in range(width)])
    for col in range(1, width + 5):
        ws.cell(row=1, column=col).font = bold
    for (_, record), opts in zip(entries, options):
        ws.append([record["term_name"], record["term_type"], record["controlled_vocabulary_options"],
                   len(opts)] + opts)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--schema", default="schema.yaml")
    parser.add_argument("--out-dir", default=BUILD_DIR)
    args = parser.parse_args()

    with open(args.schema, "r", encoding="utf-8") as handle:
        schema = yaml.safe_load(handle)
    rows, _, _, v1 = build_rows(schema)
    v1_types = {row: v1[row]["term_type"] for row in v1}

    wb = Workbook()
    wb.active.title = "README"
    write_readme(wb["README"], schema["version"])
    write_project_tab(wb.create_sheet("projectMetadata"), rows)
    write_dropdowns(wb.create_sheet("Drop-down values"), rows, v1_types)
    for tab, first_term in DATA_TABS.items():
        write_data_tab(wb.create_sheet(tab), tab, first_term, rows)
    wb._sheets.sort(key=lambda ws: TAB_ORDER.index(ws.title))

    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"FAIRe_checklist_v{schema['version']}_FULLtemplate_classic.xlsx")
    wb.save(path)
    print(f"Excel file written: {path}")


if __name__ == "__main__":
    main()
