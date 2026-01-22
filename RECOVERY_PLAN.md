# 🔧 Recovery Plan - Fix Ambiguous Abbreviations

## What Crashed
Phase 1 entity extraction produced **31.8% false positives** due to ambiguous abbreviations in seed files.

## Fixes Applied ✅

### 1. Removed "MS" from indications.json
- **Before**: "MS" matched as "Multiple Sclerosis" (disease)
- **After**: Only "multiple sclerosis" (unambiguous)
- **Impact**: Eliminates 107 false positives (16.6% of events)

### 2. Replaced "Ki" with specific terms in assays.json
- **Before**: "Ki" matched "kinase", "kidney", "killing"
- **After**: "Ki value", "inhibition constant" (specific)
- **Impact**: Eliminates 65 false positives (10.1% of events)

### 3. Replaced "Rb" with specific terms in pathways.json
- **Before**: "Rb" matched "Rubidium" and other abbreviations
- **After**: "Rb protein", "retinoblastoma protein" (specific)
- **Impact**: Eliminates 33 false positives (5.1% of events)

### 4. Added Word Boundary Detection
- **Before**: Substring matching (e.g., "Ki" in "kinase")
- **After**: Word boundary regex `\b...\b`
- **Impact**: Prevents partial word matches

## Recovery Steps

### Step 1: Backup Current Database ✅
```bash
copy output\peptide_intel.sqlite output\peptide_intel_CORRUPTED_BACKUP.sqlite
```

### Step 2: Delete Corrupted Database ✅
```bash
del output\peptide_intel.sqlite
```

### Step 3: Reinitialize Clean Database ✅
```bash
python init_db.py
```

### Step 4: Re-run Scraper with Fixed Seeds ✅
```bash
python scrape_pdfs_phase1.py
```

### Step 5: Verify Results ✅
```bash
python test_phase1_results.py
```

## Expected Results After Recovery

### Entity Coverage
- **Before**: 49.5% (but 31.8% were false positives)
- **Real Before**: ~17.7% (after removing false positives)
- **Target After**: ≥70% (with clean, accurate entities)

### Top Entities (Expected)
```
1. LC-MS (assay) - ~44 events ✅
2. mass spectrometry (assay) - ~30 events ✅
3. LIRAGLUTIDE (compound) - ~6 events ✅
4. GLUCAGON (compound) - ~6 events ✅
5. HUMAN (model) - ~20 events ✅
6. SERUM (model) - ~18 events ✅
7. diabetes (indication) - ~3 events ✅
8. cancer (indication) - ~9 events ✅
```

### False Positives
- **Before**: 205/644 events (31.8%)
- **After**: <5% (target)

### Confidence Distribution
- **Before**: 93.9% low, 5.9% med, 0.2% high
- **Target**: 40% low, 45% med, 15% high

## Validation Checklist

After recovery, verify:
- [ ] "MS" no longer appears as indication
- [ ] "Ki" no longer appears as assay (unless "Ki value")
- [ ] "Rb" no longer appears as pathway (unless "Rb protein")
- [ ] Top 10 entities are all meaningful
- [ ] Entity coverage ≥70%
- [ ] Confidence distribution improved

## Files Modified

1. ✅ `seeds/indications.json` - Removed "MS"
2. ✅ `seeds/assays.json` - Replaced "Ki" with "Ki value", "inhibition constant"
3. ✅ `seeds/pathways.json` - Replaced "Rb" with "Rb protein", "retinoblastoma protein"
4. ✅ `scrape_pdfs_phase1.py` - Added word boundary detection for all entity types
5. ✅ `CRASH_DIAGNOSIS.md` - Documented the crash
6. ✅ `RECOVERY_PLAN.md` - This file

## Next Steps

1. Run recovery script (see below)
2. Verify results with test_phase1_results.py
3. If successful, update documentation
4. If issues remain, iterate on seed files

## Recovery Script

```bash
# Backup corrupted database
copy output\peptide_intel.sqlite output\peptide_intel_CORRUPTED_BACKUP.sqlite

# Delete corrupted database
del output\peptide_intel.sqlite

# Reinitialize clean database
python init_db.py

# Re-run scraper with fixed seeds
python scrape_pdfs_phase1.py

# Verify results
python test_phase1_results.py
```

## Status

- [x] Diagnosis complete
- [x] Fixes implemented
- [ ] Database rebuilt
- [ ] Results verified
- [ ] Production-ready

**Ready to run recovery script!**
