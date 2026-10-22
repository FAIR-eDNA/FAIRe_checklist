# FAIRe_checklist

The FAIRe (FAIR eDNA) metadata checklist: the terms that make environmental DNA (eDNA), metabarcoding and targeted-assay data Findable, Accessible, Interoperable and Reusable. Guidelines and documentation are on the [FAIRe website](https://fair-edna.github.io).

The checklist is a [LinkML](https://linkml.io) model. Each term is one YAML file in `slots/`; everything else is built from these files.

---

### Latest version

**v1.0.2** (2025-07-02) is the current release. Its Japanese translation is `FAIRe_checklist_v1.0.2_JP.xlsx`.

v1.0.2 is archived on Zenodo: [doi:10.5281/zenodo.23573670](https://doi.org/10.5281/zenodo.23573670) (tag `v1.0.2` on the `v1.0.x` branch). The archive is the version as first released on 2025-07-02, with a README, LICENSE and Zenodo metadata added; the Japanese translation, added later, isn't in it.

The next release (planned as v2.0.0) is being prepared on the `dev` branch. It renames and merges some terms; see the [CHANGELOG](CHANGELOG.md). Its Excel checklist and template are built from the model into `excel/` (#147). **The files in `excel/` on `dev` are drafts of the version being prepared, not a release**; released versions are on `main`, tagged, and on Zenodo.

---

### Repository layout

| Path | What it is |
|---|---|
| `slots/` | One YAML file per term (LinkML slot). The source of truth. |
| `enums.yaml`, `types.yaml`, `classes.yaml` | Controlled vocabularies, value formats, and the tables (classes) each term belongs to. |
| `schema_header.yaml` | Schema metadata (id, version, license) and prefixes. |
| `schema.yaml` | **Generated.** The whole schema, built from the files above and committed automatically on `dev`. Don't edit or build it by hand. |
| `doc_gen_scripts/` | Build and check scripts. |
| `VALIDATION_RULES.md` | The rules every pull request is checked against. |
| `excel/` | **Generated.** The Excel checklist and full template, built from `schema.yaml` and committed automatically on `dev` (#147). On `dev` they are drafts of the next release. |
| `FAIRe_checklist_v1.0.2_JP.xlsx` | The Japanese translation of the v1.0.2 checklist. |

---

### Changing a term

1. Pull `dev`, and work on a branch off it.
2. Edit the term's file in `slots/` (or `enums.yaml`, `types.yaml`, `classes.yaml`). Don't build or commit `schema.yaml`.
3. Open a pull request into `dev`.

Every pull request is checked automatically (`.github/workflows/pr-checks.yml`) on a fresh build of the schema: it must build, pass `linkml-lint`, every example must be valid, and the slot files must follow the conventions in [VALIDATION_RULES.md](VALIDATION_RULES.md).

When the pull request is merged, `.github/workflows/build-schema.yml` rebuilds `schema.yaml` and the Excel files in `excel/`, commits what changed to `dev` (as `github-actions[bot]`; the run's log and summary say what changed) and runs the checks again. `schema.yaml` and `excel/` on `origin/dev` and `origin/main` are the source of truth, so pull `dev` after a merge. If a branch of yours conflicts on `schema.yaml` or `excel/`, take the version from `dev`.

To run the checks locally (`pip install pyyaml linkml`):

```sh
python doc_gen_scripts/check_pr.py          # all rules
python doc_gen_scripts/check_pr.py S B1     # all slot rules, and B1
```

To look at the built schema locally: `python doc_gen_scripts/build_schema.py` (`pip install pyyaml`); don't commit the result.

The Excel files are built by `generate_checklist_excel.py` and `generate_FULLtemplate_excel.py` (`pip install pyyaml openpyxl pandas`; run `build_schema.py` first). They keep the v1.0 layout: the same rows, columns and tabs, so tools that read terms by position keep working. They are dated by the last commit that changed the model or these scripts, so a rebuild only changes them when those change. To look at them locally, build into `build/` (`--out-dir build`, ignored by git); don't commit `excel/` by hand. `enums.yaml` and `classes.yaml` are edited by hand (#61).

---

### How to cite

Cite the checklist by its Zenodo DOI. [doi:10.5281/zenodo.23573669](https://doi.org/10.5281/zenodo.23573669) always points to the latest version; each version also has its own DOI (v1.0.2: [doi:10.5281/zenodo.23573670](https://doi.org/10.5281/zenodo.23573670)). Please also cite the paper:

Takahashi, M., et al. (2025). A Metadata Checklist and Data Formatting Guidelines to Make eDNA FAIR (Findable, Accessible, Interoperable, and Reusable). *Environmental DNA*, 7(3), e70100. https://doi.org/10.1002/edn3.70100

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
