# MIxS term submission

Files for proposing FAIRe slots to the GSC for MIxS (#93), using the GSC's
"MIxS New Term Request Template" spreadsheet.

`terms/<slot>.yaml` holds the answers the template asks for that are not part of
the slot itself. One file per slot; the files present decide which slots are
included. Keys (all optional except `existing_term_check`):

| Key | Template column |
|---|---|
| `mixs_term` | Slot name, for a "Reuse existing MIxS term..." row: the MIxS term's name (its title is taken from the template's Existing MIxS Terms sheet) |
| `existing_term_check` | Existing MIxS term check (one of the template's four dropdown values) |
| `related_mixs_terms` | Related MIxS term(s), as `name (MIXS:ID)`, separated by `;` |
| `justification` | Justification / proposed changes |
| `comments` | Comments / usage notes (the slot's own `comments` are notes for FAIRe users and are not copied) |
| `submitter_questions` | Submitter questions |
| `blocked` | Not a template column. Why the slot can't be submitted yet (needs discussion). The script leaves blocked slots out and lists them. |

Every other column is built from the slot in `slots/` and `enums.yaml` by
`doc_gen_scripts/generate_mixs_term_request.py`:

```sh
python doc_gen_scripts/generate_mixs_term_request.py \
  --template path/to/MIxS_New_Term_Template.xlsx --out FAIRe_MIxS_term_request.xlsx
```

A slot with a `requirement_level_condition` (e.g. "If assay_type = targeted") gets the
level that applies when the condition is not met as its Requirement level (Optional,
or the level after "Else,"), and a sentence giving FAIRe's rule at the start of its
comments ("In FAIRe this term is mandatory if assay_type = targeted; otherwise
optional."). The slots set such terms `required`/`recommended` outright (#86), which
would make them so for every MIxS sample.
