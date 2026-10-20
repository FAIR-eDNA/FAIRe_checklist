"""Pull request checks for the FAIRe checklist (#21, #48).

Run from the repository root: python doc_gen_scripts/check_pr.py
Needs linkml (pip install linkml). The rules and their IDs are in VALIDATION_RULES.md.

Prints one line per problem, e.g. "B3 Error slots/taxonID.yaml: ...". Exits 1 if any rule
at level Error fails; warnings are printed but don't fail the check.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

SCHEMA = "schema.yaml"
SLOTS_DIR = "slots"
# Everything build_schema.py reads.
BUILD_INPUTS = ["schema_header.yaml", "slots", "enums.yaml", "classes.yaml", "types.yaml", "doc_gen_scripts"]
NUMERIC_RANGES = {"integer", "float", "double", "decimal"}

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


CHECKS = {
    "B1": check_b1_build_matches,
    "B2": check_b2_lint,
    "B3": check_b3_examples,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("rules", nargs="*", help="rule IDs or groups to run (e.g. B1, B); default all")
    args = parser.parse_args()
    selected = [rule for rule in CHECKS
                if not args.rules or any(rule == r or rule.startswith(r) for r in args.rules)]

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
