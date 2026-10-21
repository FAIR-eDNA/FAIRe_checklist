"""List what changed between the committed schema.yaml and the one in the working tree.

Run from the repository root after build_schema.py: python doc_gen_scripts/schema_changes.py
Prints Markdown (added, removed and changed slots, enums, types and classes) for the
summary of the Build schema workflow (#21).
"""
import subprocess

import yaml

SECTIONS = ["slots", "enums", "types", "classes"]


def main():
    committed = subprocess.run(["git", "show", "HEAD:schema.yaml"], capture_output=True, text=True)
    old = yaml.safe_load(committed.stdout) or {} if committed.returncode == 0 else {}
    with open("schema.yaml", "r", encoding="utf-8") as handle:
        new = yaml.safe_load(handle) or {}

    lines = []
    for section in SECTIONS:
        before, after = old.get(section) or {}, new.get(section) or {}
        for label, names in [("added", sorted(set(after) - set(before))),
                             ("removed", sorted(set(before) - set(after))),
                             ("changed", sorted(n for n in set(before) & set(after) if before[n] != after[n]))]:
            if names:
                lines.append(f"- {section} {label} ({len(names)}): " + ", ".join(f"`{n}`" for n in names))
    other = sorted(k for k in set(old) | set(new) if k not in SECTIONS and old.get(k) != new.get(k))
    if other:
        lines.append("- schema header changed: " + ", ".join(f"`{k}`" for k in other))
    print("\n".join(lines) if lines else "- no changes in content (formatting only)")


if __name__ == "__main__":
    main()
