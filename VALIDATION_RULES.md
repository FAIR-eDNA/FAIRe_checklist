# FAIRe validation rules

The checks run on every pull request (#21, #48). Each rule has an ID, what is checked, and why.
**Error** = the pull request check fails. **Warning** = reported, does not fail; used while a
rule has known exceptions that wait on a decision (linked).

The rules check the committed files: `schema_header.yaml`, `slots/*.yaml`, `types.yaml`,
`enums.yaml`, `classes.yaml` and `schema.yaml`. The Excel files are not a source of truth and
are not checked.

## Build checks

| ID | Level | Check | Why |
|---|---|---|---|
| B1 | Error | `python doc_gen_scripts/build_schema.py` produces exactly the committed `schema.yaml` | The committed schema always matches its sources, so a rebuild at release gives the same file (#21). Commit `schema.yaml` together with any change to the sources. |
| B2 | Error | `linkml-lint --validate-only schema.yaml` finds no problems | LinkML's own rules. |
| B3 | Error | Every slot's examples validate against the built schema (`linkml-validate`) | An example that fails its own slot misleads users (#75, #88). |

## Slot rules

### S1. `description` is a folded block scalar (`>-`) — Error

```yaml
description: >-
  Major environmental system your sample came from. The systems identified should
  have a coarse spatial grain, to provide the general environmental context of
  where the sampling was done.
```

**Check:** the line is exactly `description: >-`; every body line is indented by exactly 2 spaces;
no body line has trailing whitespace. A blank line inside the body is legal (it means a newline in
the value) but is reported for review, since no description uses one.

**Why.** Block scalars process no escapes, so `"`, `'` and `\` are literal and quoting defects can't
happen. Two hazards are invisible in an editor and silently change the value: a line indented deeper
stops the folding (`'alpha beta\n  gamma delta'`), and a trailing space doubles a space
(`'alpha beta  gamma'`). (#46)

**Don't fix with PyYAML.** A `safe_dump` round-trip reformats the whole file and can change types
(`false` -> `"false"`). Edit the raw text, one key at a time.

### S2. Non-ASCII characters only where they carry meaning — Error

**Keep:** `µ` (U+00B5, units: `µL` is not `uL`), `β` (U+03B2, a parameter name), accented letters in
names (`é` in `José`).
**Replace or drop:** curly quotes (`’` -> `'`), `´` used as a quote (-> `'`), `®` (delete).

**Check:** any character outside ASCII that is not on the keep list.
**Why.** Every character corrupted in the Excel -> YAML conversion was a typographic one. (#47)
**Known exceptions:** `®` in `commercial_mm`, `pcr2_commercial_mm` (both removed by #42). Reported as
warnings until then.

### S3. `annotations` comes directly after `in_subset` — Error (#44)

### S4. Annotation values are strings; several values are `|`-separated — Error

`data_type: taxaRaw | taxaFinal`, never a YAML list. `linkml-lint` rejects lists, and the build
scripts split on `|`. (#50)

### S5. The five mapping lists sit directly on the slot — Error

`exact_mappings`, `close_mappings`, `related_mappings`, `narrow_mappings`, `broad_mappings` are all
present (empty ones as `[]`), and there is no `mappings:` key. (#51)

### S6. URIs are CURIEs with a declared prefix — Error

`slot_uri`, `source`, every mapping and every `see_also` entry is a CURIE whose prefix is declared in
`schema_header.yaml` (not a full URL, not an undeclared prefix). Prefixes are declared once, there. (#23)

### S7. `source` is one value or empty — Error

A CURIE for the term or publication the slot was derived from, or empty for terms FAIRe created.
Institutions without a citable URI (NOAA, INSDC, NMDC) go in `keywords`. (#52, #58)

### S8. `slot_uri` agrees with `modifications_made` — Error

- No `modifications_made` and a term as `source`: `slot_uri` is the source CURIE (the slot *is* that term).
- Any `modifications_made`: `slot_uri` is a `faire:` URI (the slot is a new FAIRe term). (#53)

### S9. A `faire:` slot has no exact mapping — Warning

A slot with its own `faire:` URI is a different term from anything it maps to, so `exact_mappings`
should be empty (the source goes under close, broad, ...).
**Known exceptions:** 23 slots (the 22 reworded slots and `study_factor`). Waits on #119/#120 (whether
to keep FAIRe's wording or use the source definition) and #116.

### S10. `faire:` URIs are well formed and unique — Error

`faire:` followed by exactly 7 digits; no two slots share a `slot_uri`. Numbers are never reused.

### S11. No retired keys — Error

None of `structured_pattern`, `settings` (#66, #82), `domain_of` (#67), `enum_values` (#61).
Patterns are a type in `types.yaml` or a plain `pattern:` on the slot.

### S12. Every slot has a `title` — Error (#95)

### S13. No double spaces in `description` — Error (#90)

### S14. `description` ends with a full stop — Warning (#96)

**Known exceptions:** 5 descriptions end with a unit note, left as guidance in #96: the four
`pcr_assay_lod/loq_LL/UL` slots ("Unit = same as pcr_assay_lod_unit") and `probe_conc` ("Unit = µM";
its unit question is #109). Waits on a decision: add the full stop or exempt them.

## Class and enum rules

### C1. Every slot is in a class, and classes list only existing slots — Error

### C2. `data_type` matches the classes a slot is in — Error

The `data_type` annotation and `classes.yaml` must name the same tables (not counting
`MetadataChecklist`). Found `pcr2_plate_id` (#134) and `pcr_rep` (#2).

### E1. No two enums have the same values — Error (#61)

### E2. An enum value's `meaning` is a CURIE with a declared prefix — Warning

Unmapped values have no `meaning`; mapped ones point to a real term (#64).
**Known exception:** `HostLifeStageEnum` (full UBERON URL, root-only enum), waits on #73.

## Not checked (on purpose)

- Every slot has an example: 4 `*_method_additional` slots may stay empty (#126).
- Match types of mappings (exact/close/broad/...): a judgement, reviewed by people (#14).
