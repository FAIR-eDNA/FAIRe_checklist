import os
from collections import OrderedDict

import yaml

# Path to the directory containing individual slot YAML files
SLOTS_DIR = "slots"
OUTPUT_SCHEMA = "schema.yaml"
GLOSSARY_FILENAME = "glossary_annotation.yaml"
ENUMS_FILENAME = "enums.yaml"
CLASSES_FILENAME = "classes.yaml"


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def split_pipe_values(raw):
    if not raw:
        return []
    return [x.strip() for x in str(raw).split("|") if x.strip()]


def normalize_context_values(raw):
    if raw is None:
        return []
    if isinstance(raw, list):
        values = []
        for item in raw:
            values.extend(normalize_context_values(item))
        return values
    return split_pipe_values(raw)


def get_slot_context(slot_def):
    """
    Extract subset context from slot definitions.

    This keeps slot YAML files as the source of truth.
    """
    annotations = slot_def.get("annotations", {})
    if not isinstance(annotations, dict):
        annotations = {}
    in_subset = slot_def.get("in_subset")
    if not in_subset:
        # Back-compat for older slot files that still store section in annotations.
        in_subset = annotations.get("section")
    return {
        "subsets": normalize_context_values(in_subset),
    }


def normalize_slots_list(raw_slots):
    if raw_slots is None:
        return []
    if isinstance(raw_slots, list):
        out = []
        for item in raw_slots:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out
    if isinstance(raw_slots, str):
        return split_pipe_values(raw_slots)
    return []


def uri_to_curie(uri, prefixes):
    """
    Replace a full URI with a CURIE when it matches a prefix expansion (longest match wins).
    Leaves non-http(s) strings and already-compact values unchanged.
    """
    if not isinstance(uri, str) or not uri:
        return uri
    if uri.startswith("linkml:") or uri.startswith("faire:"):
        return uri
    if not (uri.startswith("http://") or uri.startswith("https://")):
        return uri
    best_name = None
    best_len = 0
    for pname, pexp in prefixes.items():
        if not pexp or not isinstance(pexp, str):
            continue
        if uri.startswith(pexp) and len(pexp) > best_len:
            best_name = pname
            best_len = len(pexp)
    if not best_name:
        return uri
    local = uri[best_len:]
    if not local:
        return uri
    return f"{best_name}:{local}"


# LinkML mapping metaslots; each is a list of URIs directly on the slot.
MAPPING_KEYS = (
    "mappings",
    "exact_mappings",
    "close_mappings",
    "related_mappings",
    "narrow_mappings",
    "broad_mappings",
)


def compact_uris_in_slot(slot_def, prefixes):
    """Rewrite slot_uri and mapping lists to use schema prefix CURIEs where possible."""
    if not isinstance(slot_def, dict):
        return
    su = slot_def.get("slot_uri")
    if isinstance(su, str):
        slot_def["slot_uri"] = uri_to_curie(su, prefixes)
    for key in MAPPING_KEYS:
        mlist = slot_def.get(key)
        if not isinstance(mlist, list):
            continue
        slot_def[key] = [
            uri_to_curie(x, prefixes) if isinstance(x, str) else x for x in mlist
        ]


# Base schema structure — prefix expansions must stay in sync with compact_uris_in_slot().
SCHEMA_PREFIXES = {
    "linkml": "https://w3id.org/linkml/",
    "schema": "https://schema.org/",
    "dwc": "http://rs.tdwg.org/dwc/terms/",
    "mixs": "https://w3id.org/mixs/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcterms": "http://purl.org/dc/terms/",
    "gbif": "http://rs.gbif.org/terms/",
    "ggbn": "http://data.ggbn.org/schemas/ggbn/terms/",
    # Humboldt extension (TDWG), not the Evidence and Conclusion Ontology
    "eco": "http://rs.tdwg.org/eco/terms/",
    "nmdc": "https://w3id.org/nmdc/",
    "faire": "https://w3id.org/fairie/",
}

schema = OrderedDict(
    {
        "id": "faire:schema",
        "name": "faire_checklist",
        "description": "A LinkML schema representing the FAIRe checklist, rebuilt from individual slots.",
        "version": "1.0.2",
        "prefixes": SCHEMA_PREFIXES,
        "default_prefix": "faire",
        "imports": ["linkml:types"],
    }
)

# Load glossary (if exists) and insert first
glossary_path = os.path.join(SLOTS_DIR, GLOSSARY_FILENAME)
if os.path.exists(glossary_path):
    glossary_block = load_yaml(glossary_path)
    schema["annotations"] = glossary_block.get("annotations", {})

# Initialize containers
schema["slots"] = OrderedDict()
schema["enums"] = OrderedDict()
schema["classes"] = OrderedDict()
schema["subsets"] = OrderedDict()
slot_context = OrderedDict()

# 1) Load central enums source first.
enums_path = ENUMS_FILENAME
if os.path.exists(enums_path):
    enums_doc = load_yaml(enums_path)
    central_enums = enums_doc.get("enums", {})
    if isinstance(central_enums, dict):
        for enum_name, enum_def in central_enums.items():
            schema["enums"][enum_name] = enum_def

# 1b) Load central classes source.
classes_path = CLASSES_FILENAME
if os.path.exists(classes_path):
    classes_doc = load_yaml(classes_path)
    central_classes = classes_doc.get("classes", {})
    if isinstance(central_classes, dict):
        for class_name, class_def in central_classes.items():
            if not isinstance(class_def, dict):
                class_def = {}
            schema["classes"][class_name] = {
                "description": class_def.get(
                    "description", f"Checklist class: {class_name}."
                ),
                "slots": normalize_slots_list(class_def.get("slots")),
            }

# 2) Load all slot files (excluding glossary + enums source).
slot_files = sorted(
    f
    for f in os.listdir(SLOTS_DIR)
    if f.endswith(".yaml") and f not in {GLOSSARY_FILENAME, ENUMS_FILENAME}
)

for file_name in slot_files:
    slot_path = os.path.join(SLOTS_DIR, file_name)
    slot_content = load_yaml(slot_path)

    if "name" in slot_content:
        slot_name = slot_content["name"]
        slot_def = slot_content
        compact_uris_in_slot(slot_def, SCHEMA_PREFIXES)
        schema["slots"][slot_name] = slot_def
        slot_context[slot_name] = get_slot_context(slot_def)
    else:
        # Legacy format fallback: {slot_name: slot_def}
        for slot_name, slot_def in slot_content.items():
            compact_uris_in_slot(slot_def, SCHEMA_PREFIXES)
            schema["slots"][slot_name] = slot_def
            slot_context[slot_name] = get_slot_context(slot_def)

# Build LinkML subsets and slot membership from slot-level in_subset.
for slot_name, slot_def in schema["slots"].items():
    context = slot_context.get(slot_name, {})
    subsets = context.get("subsets", [])
    if subsets:
        slot_def["in_subset"] = subsets
        for sec in subsets:
            if sec not in schema["subsets"]:
                schema["subsets"][sec] = {
                    "description": f"Slots in checklist section: {sec}."
                }
    annotations = slot_def.get("annotations")
    if isinstance(annotations, dict) and "section" in annotations:
        # LinkML-native subset membership now lives in slot.in_subset.
        del annotations["section"]

# Keep classes.yaml as authority, but prune unknown slot references.
known_slots = set(schema["slots"].keys())
for class_name, class_def in schema["classes"].items():
    slots_for_class = class_def.get("slots", [])
    class_def["slots"] = [s for s in slots_for_class if s in known_slots]

# Always include a catch-all class.
if "MetadataChecklist" not in schema["classes"]:
    schema["classes"]["MetadataChecklist"] = {
        "description": "A metadata record based on the FAIRe checklist.",
        "slots": sorted(known_slots),
    }

if not schema["subsets"]:
    del schema["subsets"]


def convert_ordered_dict(obj):
    if isinstance(obj, OrderedDict):
        return {k: convert_ordered_dict(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: convert_ordered_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_ordered_dict(i) for i in obj]
    return obj


clean_schema = convert_ordered_dict(schema)

header_comment = (
    "# ============================\n"
    "# AUTO-GENERATED FILE\n"
    "# This file was automatically rebuilt from individual slot YAML files.\n"
    "# DO NOT EDIT THIS FILE BY HAND.\n"
    "# ============================\n\n"
)

with open(OUTPUT_SCHEMA, "w", encoding="utf-8") as handle:
    handle.write(header_comment)
    yaml.dump(clean_schema, handle, sort_keys=False, allow_unicode=True)

print(f"Merged schema written to {OUTPUT_SCHEMA}")
