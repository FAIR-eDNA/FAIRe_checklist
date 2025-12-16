import os
import yaml
from collections import OrderedDict

# Path to the directory containing individual slot YAML files
SLOTS_DIR = "slots"
OUTPUT_SCHEMA = "schema.yaml"
GLOSSARY_FILENAME = "glossary_annotation.yaml"

# Base schema structure
schema = OrderedDict({
    "id": "https://w3id.org/fairie/schema",
    "name": "faire_checklist",
    "description": "A LinkML schema representing the FAIRe checklist, rebuilt from individual slots.",
    "version": "1.0.3",
    "prefixes": {
        "linkml": "https://w3id.org/linkml/",
        "schema": "https://schema.org/",
        "dwc": "http://rs.tdwg.org/dwc/terms/",
        "mixs": "https://w3id.org/mixs/",
        "skos": "http://www.w3.org/2004/02/skos/core#"
    },
    "default_prefix": "faire",
    "imports": ["linkml:types"]
})

# Load glossary (if exists) and insert first
glossary_path = os.path.join(SLOTS_DIR, GLOSSARY_FILENAME)
if os.path.exists(glossary_path):
    with open(glossary_path, "r") as g:
        glossary_block = yaml.safe_load(g)
        annotations = glossary_block.get("annotations", {}) or {}

        # Normalise schema-level glossary annotation into a proper Annotation
        # object so LinkML tools are happy. The source file currently has:
        # annotations:
        #   glossary:
        #     Checklist: "..."
        #     (Data) term: "..."
        # LinkML expects:
        #   glossary:
        #     tag: glossary
        #     value: { Checklist: "...", (Data) term: "..." }
        if isinstance(annotations, dict) and "glossary" in annotations:
            gl = annotations["glossary"]
            if isinstance(gl, dict) and not (
                isinstance(gl.get("tag"), str) and "value" in gl
            ):
                annotations["glossary"] = {
                    "tag": "glossary",
                    "value": gl,
                }

        schema["annotations"] = annotations

# Initialize empty containers
schema["slots"] = OrderedDict()
schema["enums"] = OrderedDict()
schema["classes"] = {
    "MetadataChecklist": {
        "description": "A metadata record based on the FAIRe checklist.",
        "slots": []
    }
}


def normalize_slot_def(slot_def: dict) -> None:
    """
    BW: Normalize slot definitions so they conform to LinkML expectations:
    - Convert skos:exactMatch into slot_uri + exact_mappings
    - Move term_type into annotations to avoid unknown top-level keys
    """
    if not isinstance(slot_def, dict):
        return

    # Handle skos:exactMatch -> slot_uri + exact_mappings
    if "skos:exactMatch" in slot_def:
        raw_matches = slot_def.pop("skos:exactMatch") or []

        # Normalise to a list of strings
        if not isinstance(raw_matches, list):
            raw_matches = [raw_matches]

        iris = []
        for m in raw_matches:
            # Allow pipe-separated IRIs in a single string
            parts = str(m).split("|")
            for p in parts:
                p = p.strip()
                if p:
                    iris.append(p)

        if iris:
            # If no slot_uri is set, use the first IRI
            if "slot_uri" not in slot_def:
                slot_def["slot_uri"] = iris[0]

            existing_exact = slot_def.get("exact_mappings", [])
            if not isinstance(existing_exact, list):
                existing_exact = [existing_exact]

            for iri in iris:
                if iri not in existing_exact:
                    existing_exact.append(iri)

            slot_def["exact_mappings"] = existing_exact

    # Move term_type into annotations
    if "term_type" in slot_def:
        term_type = slot_def.pop("term_type")
        annotations = slot_def.get("annotations") or {}
        # Don't overwrite an existing annotation if one is already present
        annotations.setdefault("term_type", term_type)
        slot_def["annotations"] = annotations

    # Move top-level source into annotations so LinkML doesn't see it
    if "source" in slot_def:
        src = slot_def.pop("source")
        annotations = slot_def.get("annotations") or {}
        # Don't overwrite an existing annotation if one is already present
        annotations.setdefault("source", src)
        slot_def["annotations"] = annotations

    # Convert inline enum_values on a slot into a top-level EnumDefinition.
    # Example in slot YAML:
    #   range: assay_type_enum
    #   enum_values:
    #     targeted:
    #       meaning: targeted
    #     metabarcoding:
    #       meaning: metabarcoding
    # NOTE: LinkML treats `meaning` as a URI/CURIE. In this project we are using
    # plain-text strings (e.g. "gel electrophoresis"), so we move `meaning`
    # into `description` instead to avoid validation errors while preserving
    # the human-readable label.
    # This becomes:
    #   enums:
    #     assay_type_enum:
    #       permissible_values: { ... }
    if "enum_values" in slot_def:
        enum_vals = slot_def.pop("enum_values") or {}
        if isinstance(enum_vals, dict):
            enum_name = slot_def.get("range") or f"{slot_def.get('name', 'anonymous')}_enum"

            # Ensure enums container exists
            if "enums" not in schema or schema["enums"] is None:
                schema["enums"] = OrderedDict()

            # Clean up enum_values: convert `meaning` (plain text in this
            # project) into `description` so LinkML doesn't enforce URI/CURIE.
            cleaned_enum_vals = {}
            for pv_key, pv_def in enum_vals.items():
                if isinstance(pv_def, dict) and "meaning" in pv_def:
                    new_def = dict(pv_def)  # shallow copy
                    text = new_def.pop("meaning", None)
                    if text is not None:
                        new_def.setdefault("description", text)
                    cleaned_enum_vals[pv_key] = new_def
                else:
                    cleaned_enum_vals[pv_key] = pv_def

            existing = schema["enums"].get(enum_name)
            if existing is None:
                schema["enums"][enum_name] = {
                    "name": enum_name,
                    "permissible_values": cleaned_enum_vals,
                }
            else:
                # Merge/overwrite permissible_values conservatively
                pv = existing.setdefault("permissible_values", {})
                for k, v in cleaned_enum_vals.items():
                    if k not in pv:
                        pv[k] = v

    # Drop enum_range from merged slots to avoid EnumExpression issues in
    # linkml_runtime. The authoritative enum_range information remains in the
    # individual slot YAML files under slots/.
    if "enum_range" in slot_def:
        slot_def.pop("enum_range", None)

    # Normalise certain annotation keys into proper LinkML Annotation objects.
    # LinkML Annotation objects.
    # Original YAML has, e.g.:
    # annotations:
    #   data_type:
    #   - projectMetadata
    #   source:
    #   - DwC
    #   sample_type_specificity:
    #   - Air
    #   - HostAssociated
    # LinkML expects annotations to be either:
    #   data_type: some_value
    # or
    #   data_type:
    #     tag: data_type
    #     value: some_value
    annotations = slot_def.get("annotations")
    if isinstance(annotations, dict):
        # Keys we know are "ours" and may be lists; convert them into
        # Annotation objects so LinkML tools are happy.
        candidate_keys = (
            "data_type",
            "source",
            "modifications_made",
            "sample_type_specificity",
        )

        for key in candidate_keys:
            if key not in annotations:
                continue

            raw_val = annotations[key]

            # If it's already an Annotation-like dict, leave it alone
            if isinstance(raw_val, dict) and {"tag", "value"} <= set(raw_val.keys()):
                continue

            # Collapse lists into a comma-separated string to keep things simple
            if isinstance(raw_val, list):
                value = ", ".join(str(v) for v in raw_val)
            else:
                value = str(raw_val)

            annotations[key] = {
                "tag": key,
                "value": value,
            }

        slot_def["annotations"] = annotations


# Process all non-glossary YAML files alphabetically
slot_files = sorted(
    f for f in os.listdir(SLOTS_DIR)
    if f.endswith(".yaml") and f != GLOSSARY_FILENAME
)

for file_name in slot_files:
    slot_path = os.path.join(SLOTS_DIR, file_name)
    with open(slot_path, "r") as f:
        slot_content = yaml.safe_load(f)

        if not slot_content:
            continue

        if "name" in slot_content:
            slot_name = slot_content["name"]
            normalize_slot_def(slot_content)
            schema["slots"][slot_name] = slot_content
            schema["classes"]["MetadataChecklist"]["slots"].append(slot_name)
        else:
            for slot_name, slot_def in slot_content.items():
                normalize_slot_def(slot_def)
                schema["slots"][slot_name] = slot_def
                schema["classes"]["MetadataChecklist"]["slots"].append(slot_name)

# Sort class slot list
schema["classes"]["MetadataChecklist"]["slots"].sort()


# Convert OrderedDicts to regular dicts before dumping
from collections import OrderedDict
import yaml

# Helper function to recursively convert OrderedDict to dict
def convert_ordered_dict(obj):
    if isinstance(obj, OrderedDict):
        return {k: convert_ordered_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_ordered_dict(i) for i in obj]
    else:
        return obj

# Cleaned-up version of schema
clean_schema = convert_ordered_dict(schema)

# Header comment
header_comment = (
    "# ============================\n"
    "# AUTO-GENERATED FILE\n"
    "# This file was automatically rebuilt from individual slot YAML files.\n"
    "# DO NOT EDIT THIS FILE BY HAND.\n"
    "# ============================\n\n"
)

# Write to file (force UTF-8 so non-ASCII characters don't break on Windows)
with open("schema.yaml", "w", encoding="utf-8") as f:
    f.write(header_comment)
    yaml.dump(clean_schema, f, sort_keys=False, allow_unicode=True)

print(f"✅ Merged schema written to {OUTPUT_SCHEMA}")
