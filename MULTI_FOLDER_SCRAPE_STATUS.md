# Multi-Folder Scraping Status

## Goal
Scrape two folders into one combined database:
1. `input_pdfs/` (67 PDFs - actually 65 after filtering)
2. `input_pdfs/biohacking/` (unknown count)

## Combined Database
**Path:** `output/combined_biohacking_all.sqlite`

---

## Progress

### Folder 1: input_pdfs/ ⏳ IN PROGRESS
- **Status:** Running
- **PDFs:** 65 files
- **Domain:** biohacking_longevity
- **Command:** 
  ```bash
  python scrape_pdfs_phase1.py --domain biohacking_longevity --input-dir input_pdfs --output-db output/combined_biohacking_all.sqlite
  ```
- **Started:** In progress
- **Result:** Pending...

### Folder 2: input_pdfs/biohacking/ ⏸️ WAITING
- **Status:** Waiting for Folder 1 to complete
- **PDFs:** TBD
- **Domain:** biohacking_longevity
- **Command:** 
  ```bash
  python scrape_pdfs_phase1.py --domain biohacking_longevity --input-dir input_pdfs/biohacking --output-db output/combined_biohacking_all.sqlite
  ```
- **Will Start:** After Folder 1 completes
- **Result:** Pending...

---

## Next Steps After Scraping

1. **Verify Combined Database**
   ```bash
   python check_db_schema.py output/combined_biohacking_all.sqlite
   ```

2. **Apply Dual-Lens Export**
   ```bash
   python export_dual_lens.py output/combined_biohacking_all.sqlite biohacking_longevity
   ```

3. **Analyze Results**
   - Review `output/entities_dual_lens_biohacking_longevity.csv`
   - Review `output/events_dual_lens_biohacking_longevity.csv`
   - Review `output/dual_lens_report_biohacking_longevity.txt`

---

## Expected Outcome

- **Combined corpus** from both folders
- **Automatic deduplication** (INSERT OR IGNORE)
- **Dual-lens analysis** showing:
  - Science Research perspective
  - Biohacking Curiosity perspective
  - Different entity rankings
  - Same underlying facts

---

## Status: 🔄 SCRAPING IN PROGRESS

Last updated: 2026-01-25 10:15

Waiting for Folder 1 to complete...
