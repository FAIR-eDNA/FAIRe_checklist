"""Fill the GSC "MIxS New Term Request Template" from FAIRe slots (#93).

The slots to include are the files in gsc_submission/terms/. Each file holds the
answers the template asks for that are not part of the slot (existing-term check,
related MIxS terms, justification, ...). Everything else comes from slots/ and
enums.yaml.

Usage (from the repo root):
    python doc_gen_scripts/generate_mixs_term_request.py \
        --template MIxS_New_Term_Template.xlsx --out FAIRe_MIxS_term_request.xlsx
"""

import argparse
import ast
import os
import re
import sys

import openpyxl
import yaml

SLOTS_DIR = "slots"
ENUMS_FILENAME = "enums.yaml"
TERMS_DIR = os.path.join("gsc_submission", "terms")

SHEET = "Terms"
MIXS_TERMS_SHEET = "Existing MIxS Terms"
FIRST_ROW = 4  # rows 1-3 are the template's group, column and hint rows

# Template columns, by the header in row 2 (without the trailing " *").
COLUMNS = {
    "Slot name": "A",
    "Title": "B",
    "Description": "C",
    "Value type": "D",
    "Expected value": "E",
    "Preferred unit(s)": "F",
    "Permissible values": "G",
    "Permissible value definitions / IDs": "H",
    "Ontology / vocabulary source": "I",
    "Value syntax (optional)": "J",
    "Example value(s)": "K",
    "Multivalued?": "L",
    "Minimum value": "M",
    "Maximum value": "N",
    "Requirement level": "O",
    "Existing MIxS term check": "P",
    "Related MIxS term(s)": "Q",
    "Justification / proposed changes": "R",
    "External term mapping(s)": "S",
    "Mapping type": "T",
    "Comments / usage notes": "U",
    "References": "V",
    "Submitter questions": "W",
}

# Value type (template dropdown) -> Expected value text, as in the template's examples.
EXPECTED_VALUE = {
    "Measurement (number + unit)": "measurement value",
    "Number, no unit": "number",
    "Free text": "free text",
    "Controlled vocabulary (pick from list)": "enumeration",
    "Ontology term": "ontology term label and ID",
    "Date / time": "date and time",
    "Yes / No": "yes or no",
    "Reference (PMID, DOI or URL)": "PMID, DOI or URL",
}

# FAIRe types (types.yaml) that map to a template value type.
TYPE_VALUE_TYPE = {
    "Timestamp": "Date / time",
    "EnvoTerm": "Ontology term",
    "Reference": "Reference (PMID, DOI or URL)",
}

MAPPING_TYPES = {
    "exact_mappings": "exact",
    "close_mappings": "close",
    "broad_mappings": "broad",
    "narrow_mappings": "narrow",
    "related_mappings": "related",
}

EXISTING_TERM_CHECKS = {
    "New term – no similar MIxS term found",
    "New term – similar MIxS term exists (explain why it doesn't fit)",
    "Reuse existing MIxS term as-is",
    "Reuse existing MIxS term with changes (describe changes)",
}


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def slot_ranges(slot):
    """The slot's range plus any ranges under any_of."""
    ranges = [slot.get("range")]
    ranges += [option.get("range") for option in slot.get("any_of") or []]
    return [r for r in ranges if r and r != "Any"]


def value_type(slot, enums):
    ranges = slot_ranges(slot)
    if "boolean" in ranges:
        return "Yes / No"
    if any(r in enums for r in ranges):
        return "Controlled vocabulary (pick from list)"
    for r in ranges:
        if r in TYPE_VALUE_TYPE:
            return TYPE_VALUE_TYPE[r]
    if "integer" in ranges:
        return "Number, no unit"  # counts; MIxS models them as integers without a unit
    if "float" in ranges:
        return "Measurement (number + unit)" if slot.get("unit") else "Number, no unit"
    return "Free text"


def unit_name(slot):
    return (slot.get("unit") or {}).get("descriptive_name") or ""


def clean_description(text):
    """One line, without FAIRe's trailing "Unit = ..." (the unit has its own column)."""
    text = " ".join(str(text or "").split())
    text = re.sub(r"\s*Unit\s*=\s*[^.]*\.?$", "", text).strip()
    if text and not text.endswith("."):
        text += "."
    return text


def gsc_names_in(text, gsc_names):
    """Write the terms of this request that text names by their FAIRe name with their
    GSC-style name instead. Names inside CURIEs or URLs (dwc:..., .../miqe/...) are left."""
    swapped = []
    for faire_name, gsc_name in gsc_names.items():
        pattern = r"(?<![\w:/])" + re.escape(faire_name) + r"(?![\w])"
        if re.search(pattern, text):
            text = re.sub(pattern, gsc_name, text)
            swapped.append(f"{gsc_name} for FAIRe's {faire_name}")
    return text, swapped


def permissible_values(slot, enums):
    values, definitions = [], []
    for r in slot_ranges(slot):
        for value, spec in (enums.get(r, {}).get("permissible_values") or {}).items():
            values.append(str(value))
            spec = spec or {}
            parts = [spec.get("description") or "", f"[{spec['meaning']}]" if spec.get("meaning") else ""]
            detail = " ".join(p for p in parts if p)
            if detail:
                definitions.append(f"{value}: {detail}")
    if values and "OtherText" in slot_ranges(slot):
        values.append("other")  # FAIRe allows "other: <text>"
    return "; ".join(values), "; ".join(definitions)


def examples(slot, vtype):
    unit = unit_name(slot) if vtype.startswith("Measurement") else ""
    values = []
    for example in slot.get("examples") or []:
        value = str(example.get("value", "")).strip()
        if value:
            values.append(f"{value} {unit}" if unit else value)
    return " || ".join(values)


def requirement_level(slot):
    if slot.get("required"):
        return "Required"
    if slot.get("recommended"):
        return "Recommended"
    return "Optional"


# requirement_level_condition: "If <condition>", optionally followed by ". Else, <level>".
CONDITION = re.compile(r"^if (?P<condition>.+?)(?:\. else, (?P<otherwise>\w+))?\.?$", re.IGNORECASE)


def conditional_requirement(slot):
    """For a slot with a requirement_level_condition, the row's Requirement level (the
    level when the condition is not met) and a sentence for the comments giving FAIRe's
    rule. The slots mark such terms required or recommended outright (#86), which would
    wrongly make them so for every MIxS sample. Returns None for a slot with no condition."""
    annotations = slot.get("annotations") or {}
    text = annotations.get("requirement_level_condition")
    if not text:
        return None
    match = CONDITION.match(" ".join(str(text).split()))
    if not match:
        raise ValueError(f"requirement_level_condition not understood: {text!r}")
    level = str(annotations["requirement_level"]).lower()
    otherwise = (match["otherwise"] or "optional").lower()
    sentence = f"In FAIRe this term is {level} if {match['condition']}; otherwise {otherwise}."
    return otherwise.capitalize(), sentence


def schema_prefixes():
    """SCHEMA_PREFIXES from merge_slots.py, where the prefixes are declared once (#23)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "merge_slots.py")
    for node in ast.parse(open(path, encoding="utf-8").read()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "SCHEMA_PREFIXES" for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError("SCHEMA_PREFIXES not found in merge_slots.py")


PREFIXES = schema_prefixes()


def curie_url(ref):
    """Expand a CURIE (doi:..., gbif:miqe/...) to a link; leave anything else as it is."""
    ref = str(ref)
    prefix, sep, local = ref.partition(":")
    if sep and prefix in PREFIXES and not local.startswith("//"):
        return PREFIXES[prefix] + local
    return ref


def references(slot):
    refs = []
    source = slot.get("source")
    if source and str(source).startswith("doi:"):
        refs.append(curie_url(source))
    refs += [curie_url(s) for s in slot.get("see_also") or []]
    return "; ".join(refs)


def is_mixs(curie):
    curie = str(curie).lower()
    return curie.startswith("mixs:") or curie.startswith("https://w3id.org/mixs/")


def external_mappings(slot):
    """Non-MIxS mapping CURIEs and their type. A non-DOI source with no mapping is listed
    without a type. MIxS terms are left out: they go in the Related MIxS term(s) column."""
    curies, types = [], set()
    for key, label in MAPPING_TYPES.items():
        for curie in slot.get(key) or []:
            if not is_mixs(curie):
                curies.append(str(curie))
                types.add(label)
    source = slot.get("source")
    # A list is an unresolved source (names like "NOAA", #52), not a CURIE.
    if (not curies and isinstance(source, str) and source
            and not source.startswith("doi:") and not is_mixs(source)):
        curies.append(str(source))
    mapping_type = types.pop() if len(types) == 1 else ""
    return "; ".join(curies), mapping_type


def build_row(name, slot, answers, enums, mixs_titles, gsc_names):
    vtype = value_type(slot, enums)
    values, value_definitions = permissible_values(slot, enums)
    if vtype == "Yes / No":
        # BooleanEnum's spellings (true, TRUE, 1, yes, ...) are how FAIRe accepts yes/no;
        # the template's Yes / No value type already says that.
        values, value_definitions = "", ""
    mappings, mapping_type = external_mappings(slot)
    # Only the answers file's comments: a slot's own comments are notes for FAIRe users.
    comments = " ".join(str(answers.get("comments") or "").split())
    requirement = requirement_level(slot)
    conditional = conditional_requirement(slot)
    if conditional:
        requirement, sentence = conditional
        comments = f"{sentence} {comments}".strip()
    # A "reuse with changes" row is named after the MIxS term it changes (as in the
    # template's filter_type example); its title comes from the template's MIxS list.
    # Any other row uses the slot's name in GSC naming conventions (#94); when that
    # differs from the FAIRe name, the comments say so.
    title = slot.get("title") or ""
    # The definition is FAIRe's; in the workbook only, it names the other terms of this
    # request by their GSC-style names. The slot itself keeps the FAIRe names.
    description, swapped = gsc_names_in(clean_description(slot.get("description")), gsc_names)
    if swapped:
        comments = (f"{comments} In this request the definition uses GSC-style names "
                    f"({'; '.join(swapped)}); the FAIRe checklist's definition uses the FAIRe "
                    f"names.").strip()
    if answers.get("mixs_term"):
        name = answers["mixs_term"]
        title = mixs_titles[name]
    else:
        gsc_name = (slot.get("local_names") or {}).get("gsc-naming-conventions") or name
        if gsc_name != name:
            comments = f"FAIRe name: {name}. {comments}".strip()
            name = gsc_name
    return {
        "Slot name": name,
        "Title": title,
        "Description": description,
        "Value type": vtype,
        "Expected value": EXPECTED_VALUE.get(vtype, ""),
        "Preferred unit(s)": unit_name(slot) if vtype.startswith("Measurement") else "",
        "Permissible values": values,
        "Permissible value definitions / IDs": value_definitions,
        "Example value(s)": examples(slot, vtype),
        "Multivalued?": "Yes" if slot.get("multivalued") else "No",
        "Minimum value": slot.get("minimum_value", ""),
        "Maximum value": slot.get("maximum_value", ""),
        "Requirement level": requirement,
        "Existing MIxS term check": answers["existing_term_check"],
        "Related MIxS term(s)": answers.get("related_mixs_terms") or "",
        "Justification / proposed changes": " ".join(str(answers.get("justification") or "").split()),
        "External term mapping(s)": mappings,
        "Mapping type": mapping_type,
        "Comments / usage notes": comments,
        "References": references(slot),
        "Submitter questions": " ".join(str(answers.get("submitter_questions") or "").split()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--template", required=True, help="the GSC template (.xlsx)")
    parser.add_argument("--out", required=True, help="the filled workbook to write")
    args = parser.parse_args()

    enums = load_yaml(ENUMS_FILENAME).get("enums", {})
    workbook = openpyxl.load_workbook(args.template)
    mixs_titles = {
        row[0]: row[1] or ""
        for row in workbook[MIXS_TERMS_SHEET].iter_rows(min_row=2, values_only=True)
        if row[0]
    }
    terms, problems, blocked = [], [], []
    for filename in sorted(os.listdir(TERMS_DIR)):
        if not filename.endswith(".yaml"):
            continue
        name = filename[: -len(".yaml")]
        answers = load_yaml(os.path.join(TERMS_DIR, filename))
        if answers.get("blocked"):
            blocked.append(f"{name}: {' '.join(str(answers['blocked']).split())}")
            continue
        slot_path = os.path.join(SLOTS_DIR, filename)
        if not os.path.exists(slot_path):
            problems.append(f"{name}: no slot file {slot_path}")
            continue
        if answers.get("existing_term_check") not in EXISTING_TERM_CHECKS:
            problems.append(f"{name}: existing_term_check must be one of the template's dropdown values")
            continue
        if answers.get("mixs_term") and answers["mixs_term"] not in mixs_titles:
            problems.append(f"{name}: mixs_term {answers['mixs_term']} is not in the template's MIxS term list")
            continue
        terms.append((name, load_yaml(slot_path), answers))
    if problems:
        sys.exit("\n".join(problems))
    # FAIRe name -> GSC-style name, for the terms of this request named differently (#94)
    gsc_names = {
        name: slot["local_names"]["gsc-naming-conventions"]
        for name, slot, answers in terms
        if not answers.get("mixs_term")
        and (slot.get("local_names") or {}).get("gsc-naming-conventions", name) != name
    }
    rows = [build_row(name, slot, answers, enums, mixs_titles, gsc_names)
            for name, slot, answers in terms]

    sheet = workbook[SHEET]
    headers = {str(c.value).rstrip(" *"): c.column_letter for c in sheet[2] if c.value}
    for header, column in COLUMNS.items():
        if headers.get(header) != column:
            sys.exit(f"Template column {column} is not '{header}'; the template has changed")
    for offset, row in enumerate(rows):
        for header, value in row.items():
            sheet[f"{COLUMNS[header]}{FIRST_ROW + offset}"] = value if value != "" else None
    workbook.save(args.out)
    print(f"Wrote {len(rows)} terms to {args.out}")
    if blocked:
        print(f"Left out {len(blocked)} blocked terms:\n  " + "\n  ".join(blocked))


if __name__ == "__main__":
    main()
