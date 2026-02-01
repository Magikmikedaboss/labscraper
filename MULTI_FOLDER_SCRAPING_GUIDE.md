# Multi-Folder Scraping Guide

## What's Happening Now

We're scraping **two folders** into **one combined database**:

### Folder 1: `input_pdfs/` ⏳ RUNNING
- **65 PDFs** (stem cell, peptide, longevity research)
- **Status:** Currently processing (2% complete)
- **ETA:** ~20-30 minutes

### Folder 2: `input_pdfs/biohacking/` ⏸️ WAITING
- **Unknown count** of PDFs
- **Status:** Will start after Folder 1 completes
- **ETA:** TBD

---

## Why This Works

The scraper uses `INSERT OR IGNORE` in the database, which means:
- ✅ **Same database path** = data gets combined
- ✅ **Automatic deduplication** = no duplicate events
- ✅ **Safe to run multiple times** = idempotent
- ✅ **Incremental updates** = can add more folders later

---

## The Process

### Step 1: Scrape Folder 1 (CURRENT)
```bash
python scrape_pdfs_phase1.py \
  --domain biohacking_longevity \
  --input-dir input_pdfs \
  --output-db output/combined_biohacking_all.sqlite
```

**What it does:**
- Reads 65 PDFs from `input_pdfs/`
- Extracts research events (efficacy, toxicity, decisions, etc.)
- Extracts entities (compounds, targets, models, assays, pathways, indications)
- Stores in `output/combined_biohacking_all.sqlite`

### Step 2: Scrape Folder 2 (NEXT)
```bash
python scrape_pdfs_phase1.py \
  --domain biohacking_longevity \
  --input-dir input_pdfs/biohacking \
  --output-db output/combined_biohacking_all.sqlite
```

**What it does:**
- Reads PDFs from `input_pdfs/biohacking/`
- Extracts same types of data
- **APPENDS** to the same database (no overwrite!)
- Skips duplicates automatically

### Step 3: Apply Dual-Lens Export (FINAL)
```bash
python export_dual_lens.py \
  output/combined_biohacking_all.sqlite \
  biohacking_longevity
```

**What it does:**
- Scores all events with **two overlays**:
  - `science_research_v1` - Emphasizes models, assays, pathways
  - `biohacking_curiosity_v1` - Emphasizes compounds (2x), de-emphasizes assays
- Generates CSV exports with dual-lens columns
- Creates comparison report

---

## Expected Results

### Combined Corpus
- **All PDFs** from both folders
- **All events** from both folders
- **All entities** from both folders
- **No duplicates** (automatic deduplication)

### Dual-Lens Analysis
Different perspectives on the same data:

**Science Research Lens:**
- Models ranked high (HUMAN, MOUSE, Plasma)
- Assays ranked high (LC-MS, ELISA)
- Pathways ranked high (apoptosis, autophagy)
- Compounds ranked lower

**Biohacking Curiosity Lens:**
- Compounds ranked high (RAPAMYCIN, METFORMIN, NAD+)
- Indications ranked high (aging, longevity)
- Models ranked lower
- Assays de-emphasized

**Example Ranking Shifts:**
- RAPAMYCIN: #12 → #2 (Science → Curiosity)
- METFORMIN: #15 → #4 (Science → Curiosity)
- HUMAN (model): #4 → #8 (Science → Curiosity)

---

## Output Files

After completion, you'll have:

### 1. Combined Database
`output/combined_biohacking_all.sqlite`
- All events from both folders
- All entities from both folders
- Ready for dual-lens export

### 2. Dual-Lens Entity Export
`output/entities_dual_lens_biohacking_longevity.csv`

Columns:
```csv
entity_name, entity_type, entity_variant, event_count,
science_research_v1_score, science_research_v1_bucket,
biohacking_curiosity_v1_score, biohacking_curiosity_v1_bucket
```

### 3. Dual-Lens Event Export
`output/events_dual_lens_biohacking_longevity.csv`

Columns:
```csv
event_id, event_type, stage, outcome, evidence_snippet,
science_research_v1_score, biohacking_curiosity_v1_score,
entities_primary, entities_context, ...
```

### 4. Comparison Report
`output/dual_lens_report_biohacking_longevity.txt`

Contains:
- Top 20 entities per overlay
- Bucket distribution per overlay
- Side-by-side comparison
- Ranking shifts

---

## Current Status

### ⏳ Folder 1: IN PROGRESS
- Processing: 1/65 PDFs (2%)
- Time per PDF: ~18 seconds
- Estimated completion: ~20-30 minutes


### ⏸️ Folder 2: WAITING

- Processing: 0 / N PDFs (waiting for Folder 1 to finish)
- Time per PDF: N/A (queue is paused)
- Estimated start: When Folder 1 completes
- Description: This folder is queued and will begin processing automatically once the previous folder completes. No resources are used while waiting; status will update when active.

## What Makes This Powerful

### 1. Multi-Source Corpus
Combine PDFs from:
- Different journals
- Different time periods
- Different research groups
- Different databases (PubMed, arXiv, etc.)

### 2. Dual Analytical Perspectives
Same data, different insights:
- **Science lens:** What's scientifically rigorous?
- **Curiosity lens:** What's practically useful for biohacking?

### 3. Scalable
Can add more folders anytime:
```bash
# Add folder 3
python scrape_pdfs_phase1.py --domain biohacking_longevity --input-dir input_pdfs/new_batch --output-db output/combined_biohacking_all.sqlite

# Add folder 4
python scrape_pdfs_phase1.py --domain biohacking_longevity --input-dir input_pdfs/another_batch --output-db output/combined_biohacking_all.sqlite
```

### 4. Deduplication
- Same paper in multiple folders? No problem.
- Same event extracted twice? Automatically skipped.
- Safe to re-run on same folder.

---

## Next Steps

1. ✅ **Wait for Folder 1 to complete** (~20-30 min)
2. ⏸️ **Run Folder 2 scrape** (manual or automatic)
3. 📊 **Apply dual-lens export**
4. 📈 **Analyze results**

---

## Monitoring Progress

The scraper shows:
```text
PDFs:   2%|█ | 1/65 [00:18<19:32, 18.32s/it]
```

- `2%` = Progress percentage
- `1/65` = Current PDF / Total PDFs
- `00:18` = Time elapsed
- `19:32` = Estimated time remaining
- `18.32s/it` = Seconds per PDF

---

## Status: 🔄 SCRAPING IN PROGRESS

Folder 1 is being processed. Please wait for completion before proceeding to Folder 2.
