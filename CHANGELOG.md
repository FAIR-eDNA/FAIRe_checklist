## Changelog

All notable changes to the FAIRe metadata checklist will be documented in this file.

### [Unreleased] - on `dev`, planned as v2.0.0
#### Changed: the checklist is now a LinkML model
- Each term is one YAML file in `slots/`; `schema.yaml` is built from them (`doc_gen_scripts/build_schema.py`). The Excel checklist and templates will be generated from the model (#147).
- Every term has a URI. Terms used unchanged from another standard keep that standard's URI (e.g. `dcterms:license`); FAIRe's own and modified terms have a FAIRe URI, `https://w3id.org/faire/0000001` onwards (#53, #65).
- Mappings to MIxS, Darwin Core, Humboldt, GGBN and GenEpiO terms (exact, close, broad, related) (#14, #122, #123), and each term's source (#52).
- Each term has a name in TDWG style and in GSC style (`local_names`) (#94).
- Controlled vocabularies are LinkML enums (#61); units use UCUM codes (#62); numeric terms are numbers (#76); dates, ENVO terms and DNA sequences have a checked format (#82, #70, #98).
- Pull requests are checked automatically (`VALIDATION_RULES.md`, #21).
- License: CC BY 4.0; the build scripts are MIT (#133).
#### Renamed terms (old names kept as `aliases`)
- `dna_cleanup_0_1`, `filter_passive_active_0_1`, `habitat_natural_artificial_0_1`, `inhibition_check_0_1`, `neg_cont_0_1`, `pcr_0_1`, `pos_cont_0_1` -> `*_boolean`; they accept true/false, yes/no and 1/0, and the descriptions say which answer is true (#11, #25, #100).
- `mod_date` -> `modified` (Dublin Core) (#107).
- `confidence_score` -> `tax_assign_conf_score`, with a new definition; it is now a number (#150).
#### Merged terms
- `commercial_mm` and `custom_mm` -> `master_mix`; `pcr2_commercial_mm` and `pcr2_custom_mm` -> `pcr2_master_mix` (#42).
#### Size fractions (#26): convert existing data
- v1.0 `size_frac_low` (pre-filter size) is now `size_frac_up`; v1.0 `size_frac` (filter size) is now `size_frac_low`, following MIxS's definitions. In data made with v1.0, rename `size_frac_low` to `size_frac_up` first, then `size_frac` to `size_frac_low`.
#### Definitions and values
- `dna_sequence`: says which sequence (the representative ASV/OTU sequence) (#103).
- DNA sequences in uppercase IUPAC codes; primers and adapters may include inosine (I) (#98, #101).
- Typos, encoding errors and examples fixed throughout (#22).

### [v1.0.3] - 2025-07-31
Not released: withdrawn because of a problem in the Excel generation (#16); v1.0.2 stayed the current version.
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
Archived on Zenodo on 2026-10-22 (tag `v1.0.2`): [doi:10.5281/zenodo.23573670](https://doi.org/10.5281/zenodo.23573670).
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
