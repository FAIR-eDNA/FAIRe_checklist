"""Pull request checks for the FAIRe checklist (#21, #48).

Run from the repository root: python doc_gen_scripts/check_pr.py
Needs linkml (pip install linkml). The rules and their IDs are in VALIDATION_RULES.md.

Prints one line per problem, e.g. "B3 Error slots/taxonID.yaml: ...". Exits 1 if any rule
at level Error fails; warnings are printed but don't fail the check.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

import yaml

SCHEMA = "schema.yaml"
SLOTS_DIR = "slots"
# Everything build_schema.py reads.
BUILD_INPUTS = ["schema_header.yaml", "slots", "enums.yaml", "classes.yaml", "types.yaml", "doc_gen_scripts"]
NUMERIC_RANGES = {"integer", "float", "double", "decimal"}
GLOSSARY_FILENAME = "glossary_annotation.yaml"  # in slots/, but not a slot
# S2: non-ASCII characters that carry meaning (µL is not uL; β is a parameter name).
NON_ASCII_KEEP = {"µ", "β"}
MAPPING_KEYS = ["exact_mappings", "close_mappings", "related_mappings", "narrow_mappings", "broad_mappings"]
RETIRED_KEYS = {"structured_pattern", "settings", "domain_of", "enum_values"}
CURIE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*):(\S+)$")
FAIRE_URI = re.compile(r"^faire:\d{7}$")

ERROR = "Error"
WARNING = "Warning"

# (rule, file) -> issue. A known exception is reported as a warning until the issue is decided
# (VALIDATION_RULES.md lists them).
KNOWN_EXCEPTIONS = {
    ("B3", "slots/host_life_stage.yaml"): "#73",
}


class Problem:
    def __init__(self, rule, level, where, message):
        self.rule, self.level, self.where, self.message = rule, level, where, message

    def __str__(self):
        return f"{self.rule} {self.level} {self.where}: {self.message}"


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


# --- Build checks ---------------------------------------------------------------------


def check_b1_build_matches():
    """B1: a fresh build equals the committed schema.yaml, byte for byte."""
    with tempfile.TemporaryDirectory() as scratch:
        for name in BUILD_INPUTS:
            if os.path.isdir(name):
                shutil.copytree(name, os.path.join(scratch, name),
                                ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy(name, scratch)
        run = subprocess.run([sys.executable, "doc_gen_scripts/build_schema.py"],
                             cwd=scratch, capture_output=True, text=True)
        if run.returncode != 0:
            return [Problem("B1", ERROR, "doc_gen_scripts/build_schema.py",
                            "build failed:\n" + "\n".join(run.stderr.strip().splitlines()[-4:]))]
        with open(os.path.join(scratch, SCHEMA), "rb") as handle:
            built = handle.read()
    with open(SCHEMA, "rb") as handle:
        committed = handle.read()
    if built != committed:
        return [Problem("B1", ERROR, SCHEMA,
                        "differs from a fresh build; run python doc_gen_scripts/build_schema.py "
                        "and commit schema.yaml")]
    return []


def check_b2_lint():
    """B2: linkml-lint finds no problems in schema.yaml."""
    run = subprocess.run(["linkml-lint", "--validate-only", "--format", "json", SCHEMA],
                         capture_output=True, text=True)
    if run.returncode == 0:
        return []
    try:
        results = json.loads(run.stdout)
    except ValueError:
        return [Problem("B2", ERROR, SCHEMA, (run.stdout + run.stderr).strip())]
    return [Problem("B2", ERROR, SCHEMA, f"{r['message']} ({r.get('rule_name')}, {r.get('level')})")
            for r in results]


def slot_ranges(slot):
    """The slot's range plus any ranges under any_of."""
    ranges = [slot.get("range")]
    ranges += [option.get("range") for option in slot.get("any_of") or []]
    return {r for r in ranges if r}


def example_value(slot, value):
    """An example as a data provider would enter it: text, read the way the template reads it.

    Values of a multivalued slot are separated by `|` (#77). A value that is a number is
    read as a number only where the slot allows numbers.
    """
    items = [x.strip() for x in str(value).split("|")] if slot.get("multivalued") else [str(value)]
    numeric = slot_ranges(slot) & NUMERIC_RANGES
    if numeric:
        for i, item in enumerate(items):
            try:
                number = float(item)
            except ValueError:
                continue
            if "integer" in numeric and number.is_integer():
                items[i] = int(number)
            elif numeric - {"integer"}:
                items[i] = number
    return items if slot.get("multivalued") else items[0]


def check_b3_examples():
    """B3: every slot's examples validate against the built schema (linkml-validate)."""
    from linkml.validator import Validator
    from linkml.validator.plugins import JsonschemaValidationPlugin

    schema = load_yaml(SCHEMA)
    slots = schema.get("slots", {})
    # One class with every slot, none required, so each example can be checked on its own.
    schema["classes"]["SlotExample"] = {
        "slots": list(slots),
        "slot_usage": {name: {"required": False} for name in slots},
    }
    validator = Validator(schema, validation_plugins=[JsonschemaValidationPlugin(closed=True)])
    problems = []
    for name, slot in slots.items():
        for example in slot.get("examples") or []:
            if example.get("value") is None:
                continue
            instance = {name: example_value(slot, example["value"])}
            for result in validator.iter_results(instance, "SlotExample"):
                problems.append(Problem("B3", ERROR, f"{SLOTS_DIR}/{name}.yaml",
                                        f"example {example['value']!r}: {result.message}"))
    return problems


# --- Slot rules -----------------------------------------------------------------------


def slot_files():
    """(path, raw text, parsed YAML) for every slot file, as build_schema.py reads them."""
    for name in sorted(os.listdir(SLOTS_DIR)):
        if name.endswith(".yaml") and name != GLOSSARY_FILENAME:
            path = f"{SLOTS_DIR}/{name}"
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            yield path, text, yaml.safe_load(text) or {}


def check_s1_description_block():
    """S1: description is a `>-` block, body indented exactly 2 spaces, no trailing whitespace."""
    problems = []
    for path, text, _ in slot_files():
        lines = text.splitlines()
        start = next((i for i, line in enumerate(lines) if line.startswith("description:")), None)
        if start is None:
            continue  # a missing description is linkml-lint's to report
        if lines[start] != "description: >-":
            problems.append(Problem("S1", ERROR, path,
                                    f"line {start + 1} is {lines[start]!r}, not 'description: >-'"))
            continue
        for number, line in enumerate(lines[start + 1:], start + 2):
            if line and not line[0].isspace():
                break  # the next key
            if not line:
                problems.append(Problem("S1", WARNING, path,
                                        f"line {number}: blank line inside the description (a newline in the value)"))
            elif line != line.rstrip():
                problems.append(Problem("S1", ERROR, path, f"line {number}: trailing whitespace"))
            elif not line.startswith("  ") or line.startswith("   "):
                problems.append(Problem("S1", ERROR, path,
                                        f"line {number}: indented {len(line) - len(line.lstrip())} spaces, not 2"))
    return problems


def check_s2_non_ascii():
    """S2: no characters outside ASCII except those that carry meaning."""
    problems = []
    for path, text, _ in slot_files():
        for number, line in enumerate(text.splitlines(), 1):
            for char in sorted(set(line)):
                if ord(char) < 128 or char in NON_ASCII_KEEP:
                    continue
                name = unicodedata.name(char, "unknown")
                # Accented letters in names (José); not the bare accents (´) or other symbols.
                if name.startswith(("LATIN SMALL LETTER", "LATIN CAPITAL LETTER")):
                    continue
                problems.append(Problem("S2", ERROR, path, f"line {number}: {char!r} ({name})"))
    return problems


def check_s3_annotations_order():
    """S3: annotations comes directly after in_subset."""
    problems = []
    for path, _, slot in slot_files():
        keys = list(slot)
        if "in_subset" in keys and "annotations" in keys and \
                keys.index("annotations") != keys.index("in_subset") + 1:
            problems.append(Problem("S3", ERROR, path, "annotations doesn't come directly after in_subset"))
    return problems


def check_s4_annotation_values():
    """S4: annotation values are strings; several values are `|`-separated, never a YAML list."""
    problems = []
    for path, _, slot in slot_files():
        for key, value in (slot.get("annotations") or {}).items():
            if isinstance(value, list):
                problems.append(Problem("S4", ERROR, path,
                                        f"annotation {key} is a list; write the values as 'a | b'"))
            elif not isinstance(value, str):
                problems.append(Problem("S4", ERROR, path,
                                        f"annotation {key} is {value!r} ({type(value).__name__}), not a string"))
    return problems


def check_s5_mapping_lists():
    """S5: the five mapping lists sit directly on the slot; no mappings: key."""
    problems = []
    for path, _, slot in slot_files():
        if "mappings" in slot:
            problems.append(Problem("S5", ERROR, path, "has a mappings: key; use the five *_mappings lists"))
        for key in MAPPING_KEYS:
            if key not in slot:
                problems.append(Problem("S5", ERROR, path, f"{key} is missing (write [] if empty)"))
            elif not isinstance(slot[key], list):
                problems.append(Problem("S5", ERROR, path, f"{key} is not a list"))
    return problems


def slot_uris(slot):
    """(field, value) for every URI on a slot: slot_uri, source, mappings, see_also."""
    for key in ["slot_uri", "source"]:
        if slot.get(key) is not None:
            yield key, slot[key]
    for key in MAPPING_KEYS + ["see_also"]:
        for value in slot.get(key) or []:
            yield key, value


def check_s6_curies():
    """S6: every URI is a CURIE whose prefix is declared in schema_header.yaml."""
    prefixes = load_yaml("schema_header.yaml").get("prefixes") or {}
    problems = []
    for path, _, slot in slot_files():
        for key, value in slot_uris(slot):
            if isinstance(value, list):
                continue  # a source list is S7's to report
            match = CURIE.match(str(value))
            if not match or str(value).startswith(("http://", "https://")):
                problems.append(Problem("S6", ERROR, path, f"{key} {value!r} is not a CURIE"))
            elif match.group(1) not in prefixes:
                problems.append(Problem("S6", ERROR, path,
                                        f"{key} {value!r}: prefix {match.group(1)!r} is not declared "
                                        "in schema_header.yaml"))
    return problems


def check_s7_single_source():
    """S7: source is one value or empty."""
    return [Problem("S7", ERROR, path, f"source is a {type(slot['source']).__name__}, not one CURIE; "
                                       "put institutions without a URI in keywords")
            for path, _, slot in slot_files()
            if slot.get("source") is not None and not isinstance(slot["source"], str)]


def check_s8_slot_uri_vs_modifications():
    """S8: an unmodified slot is its source term; a modified slot has a faire: URI."""
    problems = []
    for path, _, slot in slot_files():
        modified = (slot.get("annotations") or {}).get("modifications_made")
        source, uri = slot.get("source"), str(slot.get("slot_uri"))
        if modified and not uri.startswith("faire:"):
            problems.append(Problem("S8", ERROR, path,
                                    f"modifications_made is {modified!r} but slot_uri is {uri}, not a faire: URI"))
        elif not modified and isinstance(source, str) and not source.startswith("doi:") and uri != source:
            problems.append(Problem("S8", ERROR, path,
                                    f"no modifications_made, so slot_uri should be the source {source}, not {uri}"))
    return problems


def check_s9_faire_exact_mappings():
    """S9: a slot with its own faire: URI has no exact mapping."""
    return [Problem("S9", WARNING, path, f"has a faire: slot_uri and exact_mappings {slot['exact_mappings']}")
            for path, _, slot in slot_files()
            if str(slot.get("slot_uri")).startswith("faire:") and slot.get("exact_mappings")]


def check_s10_faire_uris():
    """S10: faire: URIs are faire: + 7 digits; no two slots share a slot_uri."""
    problems, seen = [], {}
    for path, _, slot in slot_files():
        uri = str(slot.get("slot_uri"))
        if uri.startswith("faire:") and not FAIRE_URI.match(uri):
            problems.append(Problem("S10", ERROR, path, f"slot_uri {uri} is not faire: + 7 digits"))
        if uri in seen:
            problems.append(Problem("S10", ERROR, path, f"slot_uri {uri} is also used by {seen[uri]}"))
        seen.setdefault(uri, path)
    return problems


def find_keys(value, keys):
    """Every key in `keys` found anywhere in a nested dict/list."""
    if isinstance(value, dict):
        found = {k for k in value if k in keys}
        for item in value.values():
            found |= find_keys(item, keys)
        return found
    if isinstance(value, list):
        return set().union(*(find_keys(item, keys) for item in value))
    return set()


def check_s11_retired_keys():
    """S11: none of the retired keys."""
    return [Problem("S11", ERROR, path, f"retired key {key}")
            for path, _, slot in slot_files() for key in sorted(find_keys(slot, RETIRED_KEYS))]


def check_s12_title():
    """S12: every slot has a title."""
    return [Problem("S12", ERROR, path, "no title")
            for path, _, slot in slot_files() if not str(slot.get("title") or "").strip()]


def check_s13_double_spaces():
    """S13: no double spaces in description."""
    return [Problem("S13", ERROR, path, "description has a double space")
            for path, _, slot in slot_files() if "  " in str(slot.get("description") or "")]


def check_s14_full_stop():
    """S14: description ends with a full stop."""
    return [Problem("S14", ERROR, path, "description doesn't end with a full stop")
            for path, _, slot in slot_files()
            if slot.get("description") and not str(slot["description"]).endswith(".")]


CHECKS = {
    "B1": check_b1_build_matches,
    "B2": check_b2_lint,
    "B3": check_b3_examples,
    "S1": check_s1_description_block,
    "S2": check_s2_non_ascii,
    "S3": check_s3_annotations_order,
    "S4": check_s4_annotation_values,
    "S5": check_s5_mapping_lists,
    "S6": check_s6_curies,
    "S7": check_s7_single_source,
    "S8": check_s8_slot_uri_vs_modifications,
    "S9": check_s9_faire_exact_mappings,
    "S10": check_s10_faire_uris,
    "S11": check_s11_retired_keys,
    "S12": check_s12_title,
    "S13": check_s13_double_spaces,
    "S14": check_s14_full_stop,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rules", nargs="*", help="rule IDs or groups to run (e.g. B1, B); default all")
    args = parser.parse_args()
    selected = [rule for rule in CHECKS
                if not args.rules or any(rule == r or rule[0] == r for r in args.rules)]

    problems = []
    for rule in selected:
        problems.extend(CHECKS[rule]())
    for problem in problems:
        issue = KNOWN_EXCEPTIONS.get((problem.rule, problem.where))
        if issue and problem.level == ERROR:
            problem.level = WARNING
            problem.message += f" (known exception, waits on {issue})"
    for problem in problems:
        print(problem)

    errors = sum(p.level == ERROR for p in problems)
    warnings = len(problems) - errors
    print(f"Ran {', '.join(selected)}: {errors} error(s), {warnings} warning(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
