# Longevity Scraper Run - In Progress


## Status: RUNNING (started: 2026-01-30T00:00:00Z)

**Command**: `python scrape_pdfs.py --domain biohacking_longevity --input-dir input_pdfs/longevity_v1`

## Configuration
- **Domain**: biohacking_longevity (biohacking & longevity research)
- **Input Directory**: input_pdfs/longevity_v1
- **Total PDFs**: 34
- **Output Database**: output/peptide_intel.sqlite (will append to existing data)

## Seeds Loaded
- ✅ Compounds: 39
- ✅ Targets: 153
- ✅ Models: 133
- ✅ Stopwords: 146

## Progress
- Current: Processing PDF 1/34 (3%)
- Status: Running smoothly with bug fixes applied

## What This Will Add

The longevity scraper will extract:
- Research events related to aging, longevity interventions
- Compounds/drugs tested for anti-aging effects
- Biological targets related to aging pathways
- Model organisms (C. elegans, mice, etc.)
- Quantitative measurements (lifespan extension, healthspan, etc.)

## Database Note

**Important**: This scraper will ADD to the existing database that already contains:
- Neuroscience data (4,602 events from 116 PDFs)
- Any previous stem cell data

The database supports multiple domains, so all data will coexist.

## Next Steps After Completion

1. **Export longevity data**:
   ```bash
   python export_csv_v5_domain_aware.py --domain biohacking_longevity
   ```

2. **Validate the export**:
   Create a validation script similar to `test_neuroscience_export.py`

## Expected Output Files

After scraping + export:
- `output/events_export_biohacking_longevity.csv` - Longevity research events
- `output/candidates_primary_biohacking_longevity.csv` - Primary entities
- `output/run_meta_biohacking_longevity.json` - Metadata

## Estimated Time
- Scraping 34 PDFs: ~5-10 minutes
- Export: ~1 minute
- Total: ~6-11 minutes

## Multi-Domain Database

After this completes, your database will contain:
- ✅ Neuroscience corpus (116 PDFs, 4,602 events)
- 🔄 Longevity corpus (34 PDFs, TBD events)
- ✅ Stem cells corpus (if previously scraped)

You can export each domain separately using the `--domain` flag!
