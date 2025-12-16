# FAIRe_checklist

This repository stores the current and previous versions of the FAIRe metadata checklist, along with a detailed version history. Recent updates include a draft model for migration to LinkML and programmatic generation of documentation. The starting point for the slots defined in `/slots` was `FAIRe_checklist_v1.0.2.xlsx`. 

[![](https://mermaid.ink/img/pako:eNptj8tOwzAQRX_FmhVIaUiaxCReIPUFLFggxIoEIRM7iSUnLn6Ilrb_jpsWFgjLC8_4nLmaHdSKcSDQSPVZd1Rb9PBUDcifWVnBigmLLNc9OvUueNiGyEhlzZXhH2-ChVvay8sKXtFkcoPm3nl0pkNWoTth7927_zmp8yOwf9aibbk2e7QoTwCa1Vao4UwtRmruhGSeWZam7nhPx5AzsRwJMaydRY3Se7QqV5uaS3QrJDf_jvlLQACtFgyI1Y4H0Pv96LGE3dGuwPpMXgHxT8Yb6qStoBoOXlvT4UWp_sfUyrUdkIZK4yu3ZtTypaCtpv1vV_OBcb1QbrBAsqgYhwDZwQZIPJ2GSRqluMijvMD-BrAFgvMwLtICR3GCMxwV-SGArzE2CnGeFNdpkmdTHGdJhg_fItyLHQ?type=png)](https://mermaid.live/edit#pako:eNptj8tOwzAQRX_FmhVIaUiaxCReIPUFLFggxIoEIRM7iSUnLn6Ilrb_jpsWFgjLC8_4nLmaHdSKcSDQSPVZd1Rb9PBUDcifWVnBigmLLNc9OvUueNiGyEhlzZXhH2-ChVvay8sKXtFkcoPm3nl0pkNWoTth7927_zmp8yOwf9aibbk2e7QoTwCa1Vao4UwtRmruhGSeWZam7nhPx5AzsRwJMaydRY3Se7QqV5uaS3QrJDf_jvlLQACtFgyI1Y4H0Pv96LGE3dGuwPpMXgHxT8Yb6qStoBoOXlvT4UWp_sfUyrUdkIZK4yu3ZtTypaCtpv1vV_OBcb1QbrBAsqgYhwDZwQZIPJ2GSRqluMijvMD-BrAFgvMwLtICR3GCMxwV-SGArzE2CnGeFNdpkmdTHGdJhg_fItyLHQ)
_In an effort to be transparent and controlled, we have created a programmatic workflow for incorporating revisions into the FAIRe checklist._

### Do not edit the following files by hand:
- The file `schema.yaml` is regenerated on each commit from the yaml files in `/slots`. 
- Two `.xlsx` files are generated from `schema.yaml`, beginning with v1.0.3 of the checklist.

### Regenerating `schema.yaml`

If you change any files under `slots/` or update the merge logic, rebuild `schema.yaml` with:

```bash
python doc_gen_scripts/merge_slots.py
```

This script also normalizes SKOS mappings (for example, values under `skos:exactMatch`) into standard LinkML keys such as `slot_uri` and `exact_mappings`, so that downstream tools (including diagram generators) do not see unknown top-level keys.

### Generating the Mermaid ERD diagram

With the LinkML CLI installed (`pip install linkml`), you can generate a Mermaid ER diagram from the LinkML model with:

```bash
gen-erdiagram --format mermaid model.yaml > schema.mermaid
```

Notes:
- `model.yaml` imports `schema.yaml` and defines the high-level classes, so it is the recommended entry point for diagrams.
- Do not redirect the output into `schema.yaml`, as that would overwrite the auto-generated schema.

### Linting the LinkML schema

To run basic structural and style checks on the generated schema, use:

```bash
linkml-lint schema.yaml
```

---

### Latest Version

**v1.0.3**, released on 2025-07-31

---

### Changelog

For a detailed record of updates and corrections in all versions, please see the [CHANGELOG.md](https://github.com/FAIR-eDNA/FAIRe_checklist/blob/main/CHANGELOG.md).

---

### Feedback & Contributions

We welcome your feedback and suggestions to improve the FAIRe checklist and templates.  
Please report any errors, typos, or enhancement ideas by [creating an Issue](https://github.com/FAIR-eDNA/FAIRe_checklist/issues) in this repository.

---

Thank you for helping us make the FAIRe checklist better!
