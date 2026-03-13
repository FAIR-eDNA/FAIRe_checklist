# FAIRe_checklist

This repository stores the current and previous versions of the FAIRe metadata checklist, along with a detailed version history.

**Field definitions** are in `slots/` (one YAML per term). The single `.xlsx` in `latest_checklist/` is the authoritative checklist.

### For developers: build from checklist, then regenerate template

The pipeline builds the LinkML schema from the checklist Excel and slots; after that, you regenerate the Excel template from the schema — that’s what researchers use.

From repo root. Dependencies: `pip install openpyxl pyyaml pandas ruamel.yaml`

| What to run | What it does |
|-------------|--------------|
| `doc_gen_scripts/build_enums_from_checklist.py` | Reads `latest_checklist/*.xlsx` + slots → writes `enums.yaml` |
| `doc_gen_scripts/build_classes_from_checklist.py` | Reads checklist Excel + slots → writes `classes.yaml` |
| `doc_gen_scripts/merge_slots.py` | Merges slots + enums + classes → `schema.yaml` |
| `doc_gen_scripts/generate_checklist_excel.py` | Reads `schema.yaml` → Excel checklist (for download) |
| `doc_gen_scripts/generate_FULLtemplate_excel.py` | Reads `schema.yaml` → FULL Excel template (for researchers) |

Run the first three to build the schema; then run the last two to produce the Excel files researchers use.

[![](https://mermaid.ink/img/pako:eNptj8tOwzAQRX_FmhVIaUiaxCReIPUFLFggxIoEIRM7iSUnLn6Ilrb_jpsWFgjLC8_4nLmaHdSKcSDQSPVZd1Rb9PBUDcifWVnBigmLLNc9OvUueNiGyEhlzZXhH2-ChVvay8sKXtFkcoPm3nl0pkNWoTth7927_zmp8yOwf9aibbk2e7QoTwCa1Vao4UwtRmruhGSeWZam7nhPx5AzsRwJMaydRY3Se7QqV5uaS3QrJDf_jvlLQACtFgyI1Y4H0Pv96LGE3dGuwPpMXgHxT8Yb6qStoBoOXlvT4UWp_sfUyrUdkIZK4yu3ZtTypaCtpv1vV_OBcb1QbrBAsqgYhwDZwQZIPJ2GSRqluMijvMD-BrAFgvMwLtICR3GCMxwV-SGArzE2CnGeFNdpkmdTHGdJhg_fItyLHQ?type=png)](https://mermaid.live/edit#pako:eNptj8tOwzAQRX_FmhVIaUiaxCReIPUFLFggxIoEIRM7iSUnLn6Ilrb_jpsWFgjLC8_4nLmaHdSKcSDQSPVZd1Rb9PBUDcifWVnBigmLLNc9OvUueNiGyEhlzZXhH2-ChVvay8sKXtFkcoPm3nl0pkNWoTth7927_zmp8yOwf9aibbk2e7QoTwCa1Vao4UwtRmruhGSeWZam7nhPx5AzsRwJMaydRY3Se7QqV5uaS3QrJDf_jvlLQACtFgyI1Y4H0Pv96LGE3dGuwPpMXgHxT8Yb6qStoBoOXlvT4UWp_sfUyrUdkIZK4yu3ZtTypaCtpv1vV_OBcb1QbrBAsqgYhwDZwQZIPJ2GSRqluMijvMD-BrAFgvMwLtICR3GCMxwV-SGArzE2CnGeFNdpkmdTHGdJhg_fItyLHQ)
_In an effort to be transparent and controlled, we have created a programmatic workflow for incorporating revisions into the FAIRe checklist._

### Do not edit by hand
- `schema.yaml` — regenerated from slots + enums + classes.

---

### Latest Version

As described in #16, an issue was found with the excel generation scripts. v.1.02 has been restored as the correct excel files to download. v1.0.3 will be returned when the problem is fixed.
~~**v1.0.3**, released on 2025-07-31~~

---

### Changelog

For a detailed record of updates and corrections in all versions, please see the [CHANGELOG.md](https://github.com/FAIR-eDNA/FAIRe_checklist/blob/main/CHANGELOG.md).

---

### Feedback & Contributions

We welcome your feedback and suggestions to improve the FAIRe checklist and templates.  
Please report any errors, typos, or enhancement ideas by [creating an Issue](https://github.com/FAIR-eDNA/FAIRe_checklist/issues) in this repository.

---

Thank you for helping us make the FAIRe checklist better!
