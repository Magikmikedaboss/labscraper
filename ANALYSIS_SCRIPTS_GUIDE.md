# Analysis Scripts Guide

## Overview

I created 3 analysis scripts to help you validate and understand your scraper results. Here's what each one does:

---

## 1. test_results_analysis.py

**Purpose:** Comprehensive analysis of scrape results from the test database

**What it shows:**
- Overall extraction stats (events, entities)
- Entity type distribution (models, targets, compounds, etc.)
- Top entities extracted with NEW markers for recently added ones
- Event type distribution
- Confidence distribution
- Enhancement impact summary

**How to use:**
```bash
python utils/test_results_analysis.py
```

**Example output:**
```
======================================================================
ENHANCED SEEDS TEST RESULTS - 25 PDFs
======================================================================

 OVERALL EXTRACTION:
   Events: 1195
   Unique Entities: 119

  ENTITY TYPE DISTRIBUTION:
   model       :  56 unique entities |   56 total mentions
   target      :  44 unique entities |   44 total mentions
   stem_cell   :   9 unique entities |    9 total mentions
   compound    :   7 unique entities |    7 total mentions

 TOP MODELS EXTRACTED:
   Total models found: 30
    NEW neuroscience models detected: Astrocytes
     1. Astrocytes
       2. BLOOD
       3. Basal medium
   ...

 TOP TARGETS EXTRACTED:
   Total targets found: 30
    NEW targets detected: ACC, APP, BDNF, IL10, LMNA
     1. ACC
       2. AKT
   ...

 CONFIDENCE DISTRIBUTION:
   high:    8 (  0.7%)
   med :  527 ( 44.1%)
   low :  660 ( 55.2%)
```

**When to use:**
- After running a test scrape
- To validate enhanced seeds are working
- To see what entities were actually found
- To check confidence distribution

---

## 2. check_compound_extraction.py

**Purpose:** Verify compound detection is working and show what was found

**What it shows:**
- Compounds found in test scrape
- All compounds available in seed file
- Detection rate and coverage analysis
- Explanation of how compound extraction works

**How to use:**
```bash
python utils/check_compound_extraction.py
```

**Example output:**
```
======================================================================
COMPOUND EXTRACTION ANALYSIS
======================================================================

 COMPOUNDS FOUND IN TEST SCRAPE (25 PDFs):
   Total extracted: 7
   1. GLUCAGON
   2. LIRAGLUTIDE
   3. METFORMIN
   4. OCTREOTIDE
   5. PHENFORMIN
   6. RAPAMYCIN
   7. SIROLIMUS

 COMPOUNDS AVAILABLE IN SEED FILE:
   Total in seeds: 58
   
   Sample (first 20):
    1. liraglutide
    2. semaglutide
    3. dulaglutide
   ...

 YES - Your app CAN find compound names!

 Coverage:
   - Seed file has: 58 compounds
   - Test found: 7 compounds
   - Detection rate: 12.1%

 How it works:
   1. Scraper reads compounds.txt seed file
   2. Searches PDFs for exact matches (case-insensitive)
   3. Extracts compound name when found in text
   4. Tags as 'compound' entity type
```

**When to use:**
- To verify compound extraction is working
- To see which compounds were actually found
- To understand detection rates
- To answer "can my app find compound names?"

---

## 3. check_longevity_compounds.py

**Purpose:** Check which popular longevity/biohacking compounds are in your seed file

**What it shows:**
- Which longevity compounds are already in seeds ()
- Which are missing ()
- Complete list of all compounds in seeds
- Recommendations for additions

**How to use:**
```bash
python utils/check_longevity_compounds.py
```

**Example output:**
```
======================================================================
LONGEVITY COMPOUND CHECK
======================================================================

Checking for popular longevity/biohacking compounds...

 ALREADY IN SEEDS (20/20):
    nad+
    nmn
    nr
    resveratrol
    spermidine
    fisetin
    quercetin
    curcumin
    berberine
    alpha-ketoglutarate
    ca-akg
    urolithin a
    apigenin
    luteolin
    pterostilbene
    sulforaphane
    egcg
    astaxanthin
    coq10
    pqq

 MISSING (0/20):
   (none)

======================================================================
CURRENT COMPOUNDS IN SEEDS
======================================================================

Total compounds: 58

    1. liraglutide
    2. semaglutide
   ...
   40. nad+
   41. nmn
   42. resveratrol
   ...
```

**When to use:**
- To check if specific longevity compounds are in seeds
- Before adding new compounds (avoid duplicates)
- To verify recent additions were successful
- To see complete compound inventory

---

## Quick Reference

> **Note:** Run all commands from the repository root directory.

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `utils/test_results_analysis.py` | Analyze scrape results | After test scrape |
| `utils/check_compound_extraction.py` | Verify compound detection | To confirm compounds work |
| `utils/check_longevity_compounds.py` | Check longevity compound coverage | Before/after adding compounds |

---

## Common Workflows

### After Running Test Scrape:
```bash
# 1. See overall results
python utils/test_results_analysis.py

# 2. Check compound extraction specifically
python utils/check_compound_extraction.py
```

### Before Adding New Compounds:
```bash
# Check what's already there
python utils/check_longevity_compounds.py
```


### Validating Enhanced Seeds:

To validate enhanced seeds, follow these steps:

1. **Set the database path:**
    - Open the validation script (e.g., `utils/check_output_files.py`).
    - Edit the line:
       ```python
       db_path = Path("runs/test_enhanced_seeds.sqlite")
       ```
    - Change it to your target database, for example:
       ```python
       db_path = Path("runs/your_database.sqlite")
       ```

2. **Run the validation script:**
    - Execute the script in your terminal:
       ```bash
       python utils/check_output_files.py
       ```

3. **Interpret the results:**
    - The script will print a summary of seed coverage and any issues found.
    - Review the output for missing or unexpected seeds, and address any warnings or errors as needed.

### To check different compounds:

Edit `check_longevity_compounds.py` and modify the `longevity_compounds` list:
```python
longevity_compounds = [
    'your_compound_1',
    'your_compound_2',
    # ... add more
]
```

---

## Tips

1. **Run analysis scripts after every test scrape** to validate results
2. **Use check_compound_extraction.py** to answer "does my app find X?"
3. **Use check_longevity_compounds.py** before editing compounds.txt
4. **Compare results** before/after seed enhancements to measure improvement

---

## What Each Script Does NOT Do

 **Does NOT modify any files** - All scripts are read-only
 **Does NOT run the scraper** - You must run scraper first
 **Does NOT require internet** - All analysis is local
 **Does NOT change the database** - Only reads data

 **Safe to run anytime** - No side effects


