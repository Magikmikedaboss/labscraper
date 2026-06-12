# Recursive PDF Scanner - Complete Guide

## What It Does

The recursive scanner automatically:
1. **Finds ALL PDFs** in specified directories and all their subfolders
2. **Initializes the database** automatically (no manual setup needed!)
3. **Processes in parallel** with configurable workers (1-8+)
4. **Shows progress** with real-time updates
5. **Combines everything** into one master database

## Quick Start

### Scan All Your PDFs (Recommended)
```bash
python utils/scrape_all_pdfs_recursive.py --root-dirs "./input_pdfs_test" "./input_pdfs" --domain <domain> --output-db <output_db.sqlite> --workers 8
```

This will:
- Scan both `input_pdfs_test` and `input_pdfs` directories
- Find all PDFs in all subfolders
- Process with 8 workers (8x faster!)
- Create `<output_db.sqlite>` with all results

## Command Options

### Basic Usage
```bash
python utils/scrape_all_pdfs_recursive.py --root-dirs FOLDER1 [FOLDER2 ...] [OPTIONS]
```

### Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--root-dirs` | Root directories to scan (required, can specify multiple) | - | `"./input_pdfs_test" "./input_pdfs"` |
| `--domain` | Research domain | `biohacking_longevity` | `<domain>` |
| `--output-db` | Output database path | `output/all_pdfs_combined.sqlite` | `<output_db.sqlite>` |
| `--workers` | Number of parallel workers | `4` | `8` |

## Examples

### Example 1: Scan One Directory
```bash
python utils/scrape_all_pdfs_recursive.py --root-dirs "./input_pdfs" --domain <domain> --output-db <output_db.sqlite> --workers 4
```

### Example 2: Scan Multiple Directories
```bash
python utils/scrape_all_pdfs_recursive.py --root-dirs "./input_pdfs_test" "./input_pdfs" --domain <domain> --output-db <output_db.sqlite> --workers 8
```

### Example 3: Custom Output Database
```bash
python utils/scrape_all_pdfs_recursive.py --root-dirs "/path/to/input_pdfs" --domain <domain> --output-db <output_db.sqlite> --workers 6
```

### Example 4: Different Domain
```bash
python utils/scrape_all_pdfs_recursive.py --root-dirs "/path/to/input_pdfs" --domain <domain> --output-db <output_db.sqlite> --workers 8
```

## What Happens When You Run It

### Step 1: Scanning
```text
 Scanning for PDFs...
 input_pdfs_test: Found 45 PDFs
 input_pdfs: Found 298 PDFs

 Total PDFs found: 343
```

### Step 2: Folder Breakdown
```text
 Folder breakdown (15 folders):
   stemcells_v1: 65 PDFs
   neuroscience_v1: 57 PDFs
   longevity_v1: 32 PDFs
   biohacking: 28 PDFs
   ... and 11 more folders
```

### Step 3: Confirmation
```
 Ready to scrape 343 PDFs? (y/n):
```

### Step 4: Database Initialization (Automatic!)
```
======================================================================
INITIALIZING DATABASE
======================================================================

 Initializing database schema...
 Database initialized successfully
```

### Step 5: Parallel Processing
```
======================================================================
STARTING PARALLEL SCRAPE
======================================================================

PDFs: 100%|| 343/343 [05:23<00:00,  1.06it/s]
```

### Step 6: Results
```
======================================================================
SCRAPING COMPLETE
======================================================================
 Total PDFs processed: 343
 Successful: 340
 Total events extracted: 15,234
 Database: <output_db.sqlite>

======================================================================
DATABASE STATISTICS
======================================================================
 Total events in database: 15,234
  Total unique entities: 892
 Total papers: 340

======================================================================
NEXT STEP: Run dual-lens export
  python utils/export/export_dual_lens.py <output_db.sqlite> <domain>
======================================================================
```

## Performance

### Worker Recommendations

| Workers | Speed | Reliability | Best For |
|---------|-------|-------------|----------|
| 1 | 1x (slowest) | Most stable | Testing, debugging |
| 2 | 2x | Very stable | Conservative approach |
| 4 | 4x | Stable | **Recommended default** |
| 6 | 6x | Good | Faster processing |
| 8 | 8x (fastest) | Good | **Maximum speed** |

### Estimated Processing Times

For 343 PDFs:
- **1 worker (sequential):** ~86 minutes
- **4 workers:** ~21 minutes
- **8 workers:** ~11 minutes

For 100 PDFs:
- **1 worker:** ~25 minutes
- **4 workers:** ~6 minutes
- **8 workers:** ~3 minutes

## After Scraping

### View Results
```bash
# Run dual-lens export
python utils/export/export_dual_lens.py output/all_pdfs_master.sqlite biohacking_longevity
```

This creates:
- `output/entities_dual_lens_biohacking_longevity.csv` - All entities with dual scores
- `output/events_dual_lens_biohacking_longevity.csv` - All research events
- `output/dual_lens_report_biohacking_longevity.txt` - Analysis summary

### Open in Excel/Google Sheets
The CSV files can be opened directly in Excel or Google Sheets for analysis.

## Troubleshooting

### Issue: "No PDFs found"
**Solution:** Check that the directory paths are correct and contain PDF files.

### Issue: Database errors
**Solution:** The script now auto-initializes the database. If you still get errors, delete the output database and try again.

### Issue: Some PDFs fail
**Solution:** This is normal. Some PDFs may have corrupted fonts or unusual formatting. The script will continue processing the rest.

### Issue: Process is slow
**Solution:** Increase the number of workers (try `--workers 8`).

## Key Features

 **Automatic Database Initialization** - No manual setup required
 **Recursive Scanning** - Finds PDFs in all subfolders automatically
 **Multiple Root Directories** - Scan multiple folders in one run
 **Parallel Processing** - 4-8x faster with multiple workers
 **Progress Tracking** - Real-time progress bar
 **Error Handling** - Continues even if some PDFs fail
 **Folder Breakdown** - Shows which folders contain the most PDFs
 **Confirmation Prompt** - Review before starting the scrape
 **Database Statistics** - Shows final counts when complete

## Next Steps After Scraping

1. **Run dual-lens export** to analyze the data
2. **Open CSV files** in Excel/Google Sheets
3. **Query the database** directly for custom analysis
4. **Share the results** with your team

## Support

For issues or questions, check:
- `MULTI_FOLDER_SCRAPING_GUIDE.md` - Multi-folder scraping details
- `PARALLEL_SCRAPER_GUIDE.md` - Parallel processing details
- `DUAL_LENS_OVERLAY_GUIDE.md` - Analysis and export details


