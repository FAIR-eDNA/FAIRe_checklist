# FAIRe checklist v1.0.2

FAIRe (FAIR eDNA) is a metadata checklist and data templates that make environmental DNA (eDNA), metabarcoding and targeted-assay data Findable, Accessible, Interoperable and Reusable.

Guidelines and documentation: https://fair-edna.github.io

### Files

| File | What it is |
|---|---|
| `FAIRe_checklist_v1.0.2.xlsx` | The checklist: every term with its table, definition, requirement level, format, value list, example and source. |
| `FAIRe_checklist_v1.0.2_FULLtemplate.xlsx` | The data template with all terms: one sheet per table (`projectMetadata`, `sampleMetadata`, `experimentRunMetadata`, `ampData`, `stdData`, `eLowQuantData`, `taxaRaw`, `taxaFinal`) and the drop-down values. |
| `previous_versions/` | v1.0, published as supplementary material to Takahashi et al. (2025), and v1.0.1. |
| `CHANGELOG.md` | The changes in each version. |

### About this release

v1.0.2 was first released on GitHub on 2025-07-02. This release is that version (commit `bb5f0a0`) plus changes made in October 2026 for archiving on Zenodo: this README (replacing a two-line one) and two new files, `LICENSE` and `.zenodo.json`. The checklist files are unchanged.

The next version, v2.0.0, models the checklist in [LinkML](https://linkml.io) and is being prepared on the `dev` branch of https://github.com/FAIR-eDNA/FAIRe_checklist. Releases from v2.0.0 on are tagged on `main`; this one is tagged on the `v1.0.x` branch.

### How to cite

Cite the version you used by its DOI (shown on its Zenodo record), together with the paper:

Takahashi, M., et al. (2025). A Metadata Checklist and Data Formatting Guidelines to Make eDNA FAIR (Findable, Accessible, Interoperable, and Reusable). *Environmental DNA*, 7(3), e70100. https://doi.org/10.1002/edn3.70100

### License

The checklist and templates are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see [LICENSE](LICENSE)): reuse and adapt them freely, with attribution.

### Feedback

Questions and suggestions: https://github.com/FAIR-eDNA/FAIRe_checklist/issues
