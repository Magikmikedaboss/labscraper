# Biohacking Dual-Lens Scrape - In Progress

## Run Details

**Started:** 2026-01-23 ~7:00 PM
**Status:** ✅ Completed
**Completed:** 2026-01-30T14:30:00Z
**Input:** `input_pdfs/biohacking/` (26 PDFs)
**Output:** `output/biohacking_dual_lens.sqlite`
**Domain:** `biohacking_longevity` (v2 with dual-lens overlays)


## Configuration

### Enhanced Seeds Loaded
  - NAD+, NMN, resveratrol, spermidine, fisetin, quercetin, curcumin, berberine, etc.

### Dual-Lens Overlays (Configured)
1. **science_research_v1** - Emphasizes mechanisms, pathways, replication
2. **biohacking_curiosity_v1** - Emphasizes protocols, stacks, optimization

**Note:** Current scraper (`scrape_pdfs_phase1.py`) uses enhanced seeds but may not fully apply overlay emphasis yet. The overlay system is configured in the domain file and ready for future integration.


## Expected Outcomes


### Compound Detection
With 58 compounds in seeds (vs 39 before), we expect to detect 50–58 unique compounds across the corpus. 
**Acceptance criteria:** At least 50/58 compounds are found in the entity extraction results, reflecting broad coverage of the enhanced seed list.

### Target Detection
With 177 targets (vs 156 before), we expect to find 140–177 unique targets in the PDFs. 
**Acceptance criteria:** At least 140/177 targets are detected, showing the system can identify most known targets from the expanded list.

### Model Detection
With 160 models (vs 123 before), we expect to find 120–160 unique models. 
**Acceptance criteria:** At least 120/160 models are found, confirming the model detection logic covers the full range of seed models.



### PDFs to Process (26 total)

## Technical Notes

   - Normalize filenames (strip " (1)" suffix)
   - Optionally compare file checksums or canonical names
   - Only yield one entry per unique document
   - Skip or flag duplicates for review

## Next Steps (After Completion)

1. **Analyze Results**
   ```bash
   # Update test_results_analysis.py to point to new database
   python test_results_analysis.py
   ```

2. **Check Compound Extraction**
   ```bash
   python check_compound_extraction.py
   ```

3. **Verify Longevity Compounds Found**
   ```bash
   # Check which of the 20 longevity compounds were actually found
   sqlite3 output/biohacking_dual_lens.sqlite "SELECT DISTINCT entity_name FROM entities WHERE entity_type='compound' ORDER BY entity_name;"
   ```

4. **Export Results**
   ```bash
   # Use domain-aware export
   python export_csv_v5_domain_aware.py --domain biohacking_longevity --db output/biohacking_dual_lens.sqlite
   ```

5. **Compare with Previous Runs**
   - Compare entity counts before/after seed enhancements
   - Verify new compounds are being detected
   - Check confidence distribution


## Success Criteria

✅ **Minimum Goals:**

🎯 **Stretch Goals:**



The scraper populates these tables:
- `sources` - PDF metadata
- `documents` - File tracking
- `chunks` - Page-level text
- `entities` - Extracted entities (compounds, targets, models, etc.)
- `research_events` - Classified events
- `event_entities` - Entity-event links
- `event_tags` - Method tags
- `quantitative_measurements` - IC50, EC50, etc.
- `entity_relationships` - Entity comparisons

---

## Notes

- This is the first production run with the enhanced seed system
- Dual-lens overlay emphasis will be fully integrated in future versions
- Current run uses base extraction with enhanced entity coverage
- Results will validate the seed enhancement strategy

---

**Status was updated on 2026-01-30T14:30:00Z**
