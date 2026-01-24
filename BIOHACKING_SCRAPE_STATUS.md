# Biohacking Dual-Lens Scrape - In Progress

## Run Details

**Started:** 2026-01-23 ~7:00 PM
**Status:** 🔄 Running
**Input:** `input_pdfs/biohacking/` (26 PDFs)
**Output:** `output/biohacking_dual_lens.sqlite`
**Domain:** `biohacking_longevity` (v2 with dual-lens overlays)

---

## Configuration

### Enhanced Seeds Loaded
- ✅ **58 compounds** (including 19 new longevity compounds)
  - NAD+, NMN, resveratrol, spermidine, fisetin, quercetin, curcumin, berberine, etc.
- ✅ **177 targets** (21 new longevity/neuroscience targets)
- ✅ **160 models** (37 new neuroscience/metabolic models)
- ✅ **129 assays**
- ✅ **124 pathways**
- ✅ **83 indications**
- ✅ **41 neural cells**
- ✅ **146 stopwords**

### Dual-Lens Overlays (Configured)
1. **science_research_v1** - Emphasizes mechanisms, pathways, replication
2. **biohacking_curiosity_v1** - Emphasizes protocols, stacks, optimization

**Note:** Current scraper (`scrape_pdfs_phase1.py`) uses enhanced seeds but may not fully apply overlay emphasis yet. The overlay system is configured in the domain file and ready for future integration.

---

## Expected Outcomes

### Compound Detection
With 58 compounds in seeds (vs 39 before), we expect to find:
- **Longevity compounds:** NAD+, NMN, resveratrol, spermidine, etc.
- **Metabolic compounds:** metformin, rapamycin, berberine
- **Peptides:** GLP-1 agonists, mTOR inhibitors

### Target Detection
With 177 targets (vs 156 before), we expect to find:
- **Longevity targets:** TERT, SIRT1, AMPK, mTOR
- **Neuroscience targets:** BDNF, APP, MAPT
- **Metabolic targets:** FASN, ACC, CPT1

### Model Detection
With 160 models (vs 123 before), we expect to find:
- **Neuroscience models:** neurons, astrocytes, microglia
- **Metabolic models:** adipocytes, liver tissue, muscle
- **Experimental systems:** organoids, co-culture

---

## Progress Tracking

### PDFs to Process (26 total)
- [ ] 1-s2.0-S1550413123004588-main.pdf
- [ ] 262_2005_Article_BF01741328.pdf
- [ ] 11357_2013_Article_9597.pdf
- [ ] 11357_2024_Article_1484.pdf
- [ ] 12711_2024_Article_895.pdf
- [ ] 43587_2024_Article_747.pdf
- [ ] aging-03-125.pdf
- [ ] aging-11-101957.pdf
- [ ] aging-12-103725.pdf
- [ ] biomolecules-15-00018.pdf
- [ ] cei0137-0305.pdf
- [ ] cells-09-02346.pdf
- [ ] dddt-18-3643.pdf
- [ ] fgene-12-678073.pdf
- [ ] fmicb-13-935193 (1).pdf
- [ ] fmicb-13-935193.pdf
- [ ] nanomaterials-10-01121.pdf
- [ ] nat.2015.0533.pdf
- [ ] nihms-1691708.pdf
- [ ] nihms-1989323.pdf
- [ ] nihms542922.pdf
- [ ] nihms800707.pdf
- [ ] nihms870229.pdf
- [ ] nutrients-12-01344.pdf
- [ ] pnas.200911439.pdf
- [ ] sciadv.add2743.pdf

---

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

---

## Success Criteria

✅ **Minimum Goals:**
- Extract events from all 26 PDFs
- Find at least 10 of the 20 longevity compounds
- Extract 100+ unique entities
- Achieve 500+ events

🎯 **Stretch Goals:**
- Find 15+ of the 20 longevity compounds
- Extract 150+ unique entities
- Achieve 1000+ events
- 50%+ medium/high confidence events

---

## Database Schema

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

**Status will be updated when scrape completes...**
