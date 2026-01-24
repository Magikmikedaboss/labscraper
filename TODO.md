# Fixes to Apply Based on User Feedback

## Markdown Files
- [ ] DUAL_LENS_OVERLAY_GUIDE.md: Replace bold labels with headings, add language to code blocks
- [ ] MULTI_FOLDER_SCRAPING_GUIDE.md: Add CSV language to column blocks, add text to progress block

## Python Files
- [ ] export_csv_v5_domain_aware.py: Add conf_map to safe_confidence_boost for normalization
- [ ] export_dual_lens.py: Remove f-string from print, add db existence check
- [ ] scrape_pdfs_parallel.py: Improve exception handling in page loop
- [ ] utils/check_compound_extraction.py: Add db existence check
- [ ] utils/check_confidence.py: Replace lambda with function, fix print formatting
- [ ] utils/check_entity_types.py: Fix f-strings with newlines
- [ ] utils/check_longevity_compounds.py: Update file path in prints, strip comments in parsing
- [ ] utils/check_neural_cell_results.py: Fix indentation for DB queries
- [ ] utils/check_recent_run.py: Safe key access for meta dict
- [ ] utils/demo_domain_export.py: Fix relative imports

## Data Files
- [ ] runs/biohacking_longevity/run_2026-01-25_1015/run_meta.json: Update timestamp and run_id
- [ ] seeds/base/targets.txt: Normalize Unicode and hyphens (but this is a data file, perhaps update the loader)

## Completion
- [ ] Verify all changes applied correctly
