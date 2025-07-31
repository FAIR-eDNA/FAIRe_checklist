## Changelog

All notable changes to the FAIRe metadata checklist will be documented in this file.

### [v1.0.3] - 2025-07-31
#### Fixed description typos and errors: 
- none
#### Other fixes: 
- none
#### Notes:
- updated workflow to be programmatic.
   - Created LinkML yaml files for each term ("slot" in LinkML).
   - These were created from `FAIRe_checklist_v1.0.2.xlsx` and are located in `slots/`.
   - On every commit, a python script merges the slot.yaml files into the LinkML version of the checklist, `schema.yaml`.
   - Two more scripts create two excel files, `FAIRe_checklist_v{version number}.xlsx` and `{FAIRe_checklist_v{version number}_FULLtemplate.xlsx}`.
   - For version 1.0.3, all terms and metadata should be verbatim. The only change is the update to our workflow.

### [v1.0.2] - 2025-07-02
#### Fixed description typos and errors:
- `verbatimLatitude`, `verbatimLongitude`: replaced "verbatimGeodeticDatum" with "verbatimSRS"
- `verbatimSRS`: removedthe  phrase ", or verbatimCoordinates"
- `precip_temp_prep`: replaced "Chemicals" with "Temperature"
- `neg_cont_type`, `pos_cont_type`: added reference "DOI: 10.3897/mbmg.8.128689"
#### Other fixes: 
- `samp_store_loc`: moved the entry of "modifications_made" to "URI"
#### Notes:
- No structural changes to the checklist; term list remains identical to v1.0 and v1.0.1

### [v1.0.1] – 2025-06-17
#### Fixed description typos and errors:
- `targetTaxonomicScope`: replaced "targetTaxonomicPCR" with "targetTaxonomicAssay"
#### Notes:
- No structural changes to the checklist; term list remains identical to v1.0

### [v1.0] – 2025-01-21
#### Added
- Published as supplementary material in [Takahashi et al. (2025)](https://doi.org/10.1002/edn3.70100)  
- Includes support for metabarcoding and targeted assay eDNA workflows
