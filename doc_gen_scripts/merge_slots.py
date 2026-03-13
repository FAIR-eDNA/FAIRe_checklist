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


def to_permissible_values(enum_values):
    """
    Normalize slot-local enum_values into LinkML permissible_values format.
    """
    permissible = OrderedDict()
    if not isinstance(enum_values, dict):
        return permissible

    for key, val in enum_values.items():
        if isinstance(val, dict):
            # Keep existing meaning/description if present.
            permissible[key] = {
                "meaning": val.get("meaning", key),
                **({"description": val["description"]} if "description" in val else {}),
            }
        else:
            permissible[key] = {"meaning": key}
    return permissible


# Base schema structure
schema = OrderedDict(
    {
        "id": "tbd: a value like https://w3id.org/fairie/schema",
        "name": "faire_checklist",
        "description": "A LinkML schema representing the FAIRe checklist, rebuilt from individual slots.",
        "version": "1.0.3",
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "schema": "https://schema.org/",
            "dwc": "http://rs.tdwg.org/dwc/terms/",
            "mixs": "https://w3id.org/mixs/",
            "skos": "http://www.w3.org/2004/02/skos/core#",
        },
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
    loaded_slot_names = []

    if "name" in slot_content:
        slot_name = slot_content["name"]
        slot_def = slot_content
        schema["slots"][slot_name] = slot_def
        slot_context[slot_name] = get_slot_context(slot_def)
        loaded_slot_names.append(slot_name)
    else:
        # Legacy format fallback: {slot_name: slot_def}
        for slot_name, slot_def in slot_content.items():
            schema["slots"][slot_name] = slot_def
            slot_context[slot_name] = get_slot_context(slot_def)
            loaded_slot_names.append(slot_name)

    # If slot still contains local enum_values, keep backward compatibility:
    # - lift into top-level enums
    # - keep rendered enum_values in slot output
    for slot_name in loaded_slot_names:
        current_slot = schema["slots"][slot_name]
        local_enum_values = current_slot.get("enum_values")
        if isinstance(local_enum_values, dict) and local_enum_values:
            enum_name = current_slot.get("range")
            if (
                not enum_name
                or not isinstance(enum_name, str)
                or not enum_name.endswith("_enum")
            ):
                enum_name = f"{slot_name}_enum"
                current_slot["range"] = enum_name

            if enum_name not in schema["enums"]:
                schema["enums"][enum_name] = {
                    "description": f"Controlled vocabulary for {slot_name}.",
                    "permissible_values": to_permissible_values(local_enum_values),
                }

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

# 3) Render central enum definitions back into each slot for downstream tools
# that currently expect enum_values next to the slot.
for slot_name, slot_def in schema["slots"].items():
    slot_range = slot_def.get("range")
    if not isinstance(slot_range, str):
        continue
    enum_def = schema["enums"].get(slot_range)
    if not isinstance(enum_def, dict):
        continue
    permissible = enum_def.get("permissible_values", {})
    if isinstance(permissible, dict):
        rendered = OrderedDict()
        for value_key, value_def in permissible.items():
            if isinstance(value_def, dict):
                rendered[value_key] = {"meaning": value_def.get("meaning", value_key)}
            else:
                rendered[value_key] = {"meaning": value_key}
        slot_def["enum_values"] = rendered

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
