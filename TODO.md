# TODO: Fix Issues in export_csv_v4_professional.py and utils/axon_domains.py

## export_csv_v4_professional.py
- [x] Add directory creation for OUTPUT_DIR using OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
- [x] Update total_events calculation in write_run_meta to include "other" bucket
- [x] Add "other" to confidence_distribution in write_run_meta
- [x] Change specific f-strings without placeholders to plain strings (Ruff F541)

## utils/axon_domains.py
- [x] Add os.path.isfile and os.access checks in get_domain_by_id
- [x] Add OSError to exception handling in get_domain_by_id

## Verification
- [x] Run export_csv_v4_professional.py to ensure no errors (failed due to missing DB, but no syntax errors)
- [x] Run utils/axon_domains.py to ensure no errors (ran successfully)
