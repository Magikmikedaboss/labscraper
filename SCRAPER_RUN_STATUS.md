# Neuroscience Scraper Run - In Progress

## Status: 🔄 RUNNING


- **Started**: 2026-01-29T14:23:00Z
- **Command**: `python scrape_pdfs.py --domain neuroscience --input-dir input_pdfs/neuroscience_v1`

## Configuration
- **Domain**: neuroscience
- **Input Directory**: input_pdfs/neuroscience_v1
- **Total PDFs**: 116
- **Output Database**: output/peptide_intel.sqlite

## Seeds Loaded
- ✅ Compounds: 39
- ✅ Targets: 153
- ✅ Models: 133
- ✅ Stopwords: 146

## Progress
- Current: Processing PDF 1/116 (1%)
- Status: Running smoothly with bug fixes applied

## Bug Fixes Applied Before This Run
All 5 critical runtime bugs were fixed before starting this scraper run:

1. ✅ **export_csv_v5_domain_aware.py** - SQLite connection leaks fixed
2. ✅ **export_csv_v4_professional.py** - Confidence KeyError handling added
3. ✅ **pattern_intelligence.py** - DB cursor context fixed
4. ✅ **test_domain_export.py** - NameError on empty rows fixed
5. ✅ **show_v4_exports.py** - Duplicate read and KeyError fixed

## What Happens Next

### 1. Scraping Phase (Current)
The scraper will:
- Extract text from all 116 PDFs
- Identify research events (efficacy, toxicity, decisions, etc.)
- Extract entities (compounds, targets, models, stem cells)
- Extract quantitative measurements (IC50, EC50, etc.)
- Detect entity relationships
- Store everything in SQLite database

### 2. Export Phase (After Scraping)
Once scraping completes, run:
```bash
python export_csv_v5_domain_aware.py --domain neuroscience
```

This will:
- Export events to CSV with domain awareness
- Export primary entities (candidates)
- Apply confidence boosting
- Demote process words to context
- Generate run metadata JSON

### 3. Validation Phase
Then validate the export:
```bash
python test_neuroscience_export.py
```

## Expected Output Files

After scraping + export:
- `output/peptide_intel.sqlite` - Main database
- `output/events_export_neuroscience.csv` - All research events
- `output/candidates_primary_neuroscience.csv` - Primary entities
- `output/run_meta_neuroscience.json` - Metadata

## Estimated Time
- Scraping 116 PDFs: ~15-30 minutes (depends on PDF size/complexity)
- Export: ~1-2 minutes
- Total: ~20-35 minutes

## Notes
- The scraper commits after each PDF, so progress is saved incrementally
- If it crashes, you can resume and it will skip already-processed PDFs
- All critical bugs have been fixed, so it should run smoothly
- Previous export data will be overwritten when you run the export command
