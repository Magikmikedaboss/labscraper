# Quick Start Guide

## Overview
AXON is a modular research intelligence engine for extracting structured signals from PDF documents. It supports multiple research domains and provides parallel processing for optimal performance.

## Typical Workflow
1. Collect PDFs or discover sources via RSS
2. Place PDFs in a domain folder
3. Run the engine
4. Review extracted events and entities
5. Export results to CSV
6. Analyze results or import into dashboards

## Prerequisites
- Python 3.11+
- Required packages (install with `pip install -r requirements.txt`)

## Quick Setup

### 1. Database Initialization

Most users can skip manual DB setup.

The canonical production/dev database at `db/runs.sqlite` is initialized explicitly.
Running `utils/run_engine.py` against that path will raise `SystemExit` if the schema tables are missing.
Initialize it first with `python utils/init_db.py db/runs.sqlite --force` when you need to recreate it.

Only non-canonical/test databases are auto-initialized.
Run `python utils/init_db.py db/local.sqlite` when you need an isolated local or CI test database.
Use `db/local.sqlite` for scratch/test runs and `db/runs.sqlite` for the default shared database.

```bash
# Optional isolated local/CI test DB initialization
python utils/init_db.py db/local.sqlite
```

### 2. Prepare Input Files
Place your PDF files in the appropriate input directory:
- Default: `input/pdfs/`
- Domain-specific: `input/pdfs/{domain_name}/`

### 3. Run Scraper

#### Single Domain Processing
```bash
# Basic usage
python utils/run_engine.py --domain construction_science --input-dir input/pdfs/construction_science

# With custom output database
python utils/run_engine.py --domain construction_science --input-dir input/pdfs/construction_science --output-db custom.db
```

#### Parallel Processing (Recommended for large datasets)
```bash
# 4 parallel workers (recommended)
python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input/pdfs/construction_science --workers 4

# 8 parallel workers (for powerful systems)
python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input/pdfs/construction_science --workers 8

# Custom output database
python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input/pdfs/construction_science --output-db custom.db --workers 4
```

**Note**: Use `input/pdfs` (root) only for multi-domain ingestion. For single-domain runs, use `input/pdfs/{domain_name}`.
The parallel scraper default input directory is `input/pdfs`, so passing `--input-dir` explicitly is recommended when using domain-specific subdirectories.
### 4. Export Results
```bash
# Basic export (reads from db/runs.sqlite)
python utils/export_csv.py --domain construction_science

# Dual-lens export (advanced analysis)
python utils/export/export_dual_lens.py db/runs.sqlite construction_science
```

⚠ **Recovery / Reinitialization**

If `db/runs.sqlite` becomes corrupted or you need a clean restart, the safer recovery path is:

1. `python utils/init_db.py db/runs.sqlite --force` to create a fresh schema in `db/runs.sqlite`.
2. Re-run ingestion with `python utils/run_engine.py ... --output-db db/runs.sqlite` to repopulate the database.

Be aware that `python utils/run_engine.py ... --output-db db/runs.sqlite` will both initialize the database and reprocess PDFs, so it is not just a schema-only reset. Use `utils/init_db.py` when you want to create the database first and ingest documents separately. The helper in `utils/db_init.py` raises a `RuntimeError` for the canonical `db/runs.sqlite` path, so the test-only helper is not the supported entrypoint for this recovery flow.

`utils/db_init.py` is test-only and should not be used for this recovery flow.

`utils/export_csv.py` currently reads from `db/runs.sqlite`.

If you process data into a custom database, use:

`utils/export/export_dual_lens.py <your_db_path> <domain>`

### 5. RSS Feed Discovery (Optional)
```bash
# Test configured feeds
python tools/test_feeds.py --config config/feeds.json --save-working

# Preview RSS ingestion
python run_rss_ingest.py --dry-run
```

## Supported Domains
- `construction_science` - Building materials, structural engineering, construction methods
- `biohacking_longevity` - Health optimization, longevity research, biohacking
- `neuroscience_cognition` - Brain research, neural systems, cognitive science
- `drug_discovery` - Pharmaceutical research, compound development
- `methods_tooling` - Research methods, tools, and techniques
- `stem_cells_regen` - Stem cells and regenerative medicine

## File Structure

### Core Scripts
- `utils/scrape_pdfs_parallel.py` - **Recommended**: Parallel PDF processing (4-8x faster)
- `utils/run_engine.py` - Single-threaded processing
- `utils/export/export_dual_lens.py` - Advanced dual-lens analysis
- `utils/export_csv.py` - Standard CSV export

### Configuration
- `config/domains/` - Domain-specific configurations
- `seeds/` - Entity seed lists for different domains
- `lenses/` - Overlay configurations for dual-lens analysis

### Output
- `db/runs.sqlite` - Main database with extracted research events
- `exports/` - Exported CSV files and analysis results
- `logs/` - Processing logs and error reports

## Performance Tips

### For Large PDF Collections
1. Use parallel processing with 4-8 workers
2. Process PDFs in domain-specific folders
3. Monitor memory usage for very large files

### For Better Accuracy
1. Ensure seed files are populated for your domain
2. Use domain-specific configurations
3. Validate results with manual spot-checks

## Troubleshooting

### Common Issues
- **Import errors**: Ensure all required packages are installed
- **Database errors**: run `python utils/run_engine.py --domain construction_science --input-dir input/pdfs/construction_science --output-db db/runs.sqlite` to initialize schema on first run
- **Missing entities**: Check seed files in `seeds/` directory

### Getting Help
- Check `logs/` for detailed error messages
- Review domain configurations in `config/domains/`
- Verify input PDF files are not corrupted

## Next Steps
1. Explore the exported CSV files in `exports/`
2. Use dual-lens analysis for deeper insights
3. Customize seed files for your specific research needs
4. Set up automated processing for regular updates

## Related Docs
- [EXPORT_FILES_GUIDE.md](EXPORT_FILES_GUIDE.md) - Export outputs and file meanings
- [EXPORT_CONFIGURATION_GUIDE.md](EXPORT_CONFIGURATION_GUIDE.md) - Advanced export behavior and troubleshooting
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Validation and regression workflow

