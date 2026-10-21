# FAIRe_checklist

The FAIRe (FAIR eDNA) metadata checklist: the terms that make environmental DNA (eDNA), metabarcoding and targeted-assay data Findable, Accessible, Interoperable and Reusable. Guidelines and documentation are on the [FAIRe website](https://fair-edna.github.io).

The checklist is a [LinkML](https://linkml.io) model. Each term is one YAML file in `slots/`; everything else is built from these files.

---

### Latest version

**v1.0.2** (2025-07-02) is the current release: `FAIRe_checklist_v1.0.2.xlsx` (checklist, also in `latest_checklist/`), `FAIRe_checklist_v1.0.2_FULLtemplate.xlsx` (data template) and `FAIRe_checklist_v1.0.2_JP.xlsx` (Japanese).

The next release (planned as v2.0.0) is being prepared on the `dev` branch. It renames and merges some terms; see the [CHANGELOG](CHANGELOG.md). Its Excel checklist and templates will be generated from the model (#147).

---

### Repository layout

| Path | What it is |
|---|---|
| `slots/` | One YAML file per term (LinkML slot). The source of truth. |
| `enums.yaml`, `types.yaml`, `classes.yaml` | Controlled vocabularies, value formats, and the tables (classes) each term belongs to. |
| `schema_header.yaml` | Schema metadata (id, version, license) and prefixes. |
| `schema.yaml` | **Generated.** The whole schema, built from the files above. Don't edit it by hand. |
| `doc_gen_scripts/` | Build and check scripts. |
| `VALIDATION_RULES.md` | The rules every pull request is checked against. |
| `latest_checklist/`, `FAIRe_checklist_v1.0.2*.xlsx` | The Excel checklist and template of the current release (v1.0.2). |

---

### Changing a term

1. Work on a branch off `dev`, and edit the term's file in `slots/` (or `enums.yaml`, `types.yaml`, `classes.yaml`).
2. Rebuild the schema from the repository root (`pip install pyyaml`):
   ```sh
   python doc_gen_scripts/build_schema.py
   ```
3. Commit `schema.yaml` together with your change, and open a pull request into `dev`.

Every pull request is checked automatically (`.github/workflows/pr-checks.yml`): `schema.yaml` must equal a fresh build, the schema must pass `linkml-lint`, every example must be valid, and the slot files must follow the conventions in [VALIDATION_RULES.md](VALIDATION_RULES.md). To run the checks locally (`pip install pyyaml linkml`):

```sh
python doc_gen_scripts/check_pr.py          # all rules
python doc_gen_scripts/check_pr.py S B1     # all slot rules, and B1
```

The Excel scripts (`generate_checklist_excel.py`, `generate_FULLtemplate_excel.py`) are being updated for the model (#147). `build_enums_from_checklist.py` and `build_classes_from_checklist.py` are retired: `enums.yaml` and `classes.yaml` are edited by hand.

---

### Changelog

For a record of changes in all versions, see the [CHANGELOG](CHANGELOG.md).

---

### License

The FAIRe checklist, the schema (`slots/`, `enums.yaml`, `classes.yaml`, `types.yaml`, `schema.yaml`) and the templates are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see [LICENSE](LICENSE)): reuse and adapt them freely, with attribution.
The build scripts in `doc_gen_scripts/` are licensed under the [MIT License](doc_gen_scripts/LICENSE).

---

### Feedback & Contributions

We welcome your feedback and suggestions to improve the FAIRe checklist and templates.
Please report any errors, typos, or enhancement ideas by [creating an Issue](https://github.com/FAIR-eDNA/FAIRe_checklist/issues) in this repository.

---

Thank you for helping us make the FAIRe checklist better!
