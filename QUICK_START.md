# Quick Start Guide

## Overview
The Peptide Intelligence Scraper is a powerful tool for extracting research intelligence from PDF documents. It supports multiple research domains and provides parallel processing for optimal performance.

## Prerequisites
- Python 3.8+
- Required packages (install with `pip install -r requirements.txt`)

## Quick Setup

### 1. Initialize Database
```bash
python init_db.py
```

### 2. Prepare Input Files
Place your PDF files in the appropriate input directory:
- Default: `input/pdfs/`
- Domain-specific: `input/pdfs/{domain_name}/`

### 3. Run Scraper

#### Single Domain Processing
```bash
# Basic usage
python utils/run_engine.py --domain construction_science --input-dir input/pdfs

# With custom output database
python utils/run_engine.py --domain construction_science --input-dir input/pdfs --output-db custom.db
```

#### Parallel Processing (Recommended for large datasets)
```bash
# 4 parallel workers (recommended)
python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input/pdfs --workers 4

# 8 parallel workers (for powerful systems)
python utils/scrape_pdfs_parallel.py --domain construction_science --input-dir input/pdfs --workers 8
```

### 4. Export Results
```bash
# Basic export
python utils/export_csv_v5_domain_aware.py --db-path db/runs.sqlite --domain construction_science

# Dual-lens export (advanced analysis)
python utils/export_dual_lens.py --db-path db/runs.sqlite --domain construction_science
```

## Supported Domains
- `construction_science` - Building materials, structural engineering, construction methods
- `biohacking_longevity` - Health optimization, longevity research, biohacking
- `neuroscience` - Brain research, neural systems, cognitive science
- `drug_discovery` - Pharmaceutical research, compound development
- `methods_tooling` - Research methods, tools, and techniques

## File Structure

### Core Scripts
- `utils/scrape_pdfs_parallel.py` - **Recommended**: Parallel PDF processing (4-8x faster)
- `utils/run_engine.py` - Single-threaded processing
- `utils/export_dual_lens.py` - Advanced dual-lens analysis
- `utils/export_csv_v5_domain_aware.py` - Standard CSV export

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
- **Database errors**: Run `python init_db.py` to initialize schema
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