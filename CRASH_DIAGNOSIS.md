# 🔴 CRASH DIAGNOSIS: Ambiguous Abbreviations

## What Crashed
The Phase 1 entity extraction system is producing **catastrophic false positives** due to ambiguous abbreviations in seed files.

## Root Causes

### 1. "MS" Ambiguity ⚠️ CRITICAL (107 false positives)
**Problem**:
- `indications.json` contains "MS" = "Multiple Sclerosis"
- Peptide PDFs use "MS" = "Mass Spectrometry"
- Every mention of "LC-MS", "MS/MS", "mass spec" tagged as disease

**Evidence**:
```
Top entity: MS (indication): 107 events ❌
Should be: mass spectrometry (assay)
```

**Impact**: 16.6% of all events (107/644) have wrong entity type

---

### 2. "Ki" Over-extraction ⚠️ HIGH (65 false positives)
**Problem**:
- `assays.json` contains "Ki" = "inhibition constant"
- Matches: "kinase", "kidney", "killing", "kinesin", etc.
- No word boundary detection

**Evidence**:
```
Top entity: Ki (assay): 65 events ❌
Likely matches: "kinase", "kidney", "killing"
```

**Impact**: 10.1% of all events (65/644) have wrong entity

---

### 3. "Rb" Ambiguity ⚠️ MEDIUM (33 false positives)
**Problem**:
- `pathways.json` contains "Rb" = "Retinoblastoma protein"
- Chemistry PDFs use "Rb" = "Rubidium" (element)
- Ambiguous in scientific text

**Evidence**:
```
Top entity: Rb (pathway): 33 events ❌
Could be: Rubidium, Retinoblastoma, or abbreviation
```

**Impact**: 5.1% of all events (33/644) have wrong entity

---

## Total Data Corruption

**False Positives**: 205/644 events (31.8%) have wrong entities
- MS: 107 events
- Ki: 65 events
- Rb: 33 events

**Actual Entity Coverage**: 
- Reported: 49.5% (319/644)
- Real (after removing false positives): ~17.7% (114/644)
- **WORSE than before Phase 1!** (was 13%)

---

## Why This Crashed the System

1. **Data Quality**: 31.8% false positive rate makes data unusable
2. **Dashboard Filters**: Filtering by "MS" shows mass spec papers as disease research
3. **Entity Rankings**: Top entities are all false positives
4. **Confidence Scoring**: False entities boost confidence incorrectly
5. **Export Quality**: CSV exports contain corrupted data

---

## Emergency Fix Required

### Immediate Actions (CRITICAL)
1. ✅ Remove "MS" from indications.json
2. ✅ Remove "Ki" from assays.json metrics
3. ✅ Remove "Rb" from pathways.json
4. ✅ Add word boundary detection for all extractions
5. ✅ Add minimum length requirement (≥3 chars for abbreviations)

### Short-term Actions (HIGH)
1. Add context-aware extraction (check surrounding words)
2. Add disambiguation rules for common conflicts
3. Add stopword list for chemical elements (Rb, Na, K, Ca, etc.)
4. Improve entity-event linking with confidence scores

### Long-term Actions (MEDIUM)
1. Build abbreviation disambiguation system
2. Add domain-specific context detection
3. Implement entity validation against known databases
4. Add human-in-the-loop review for ambiguous cases

---

## Recommended Seed File Changes

### indications.json
```diff
- "MS",  ❌ REMOVE (conflicts with Mass Spectrometry)
+ "multiple sclerosis",  ✅ KEEP (unambiguous)
```

### assays.json (metrics)
```diff
- "Ki",  ❌ REMOVE (too short, matches "kinase", "kidney")
+ "Ki value",  ✅ ADD (more specific)
+ "inhibition constant",  ✅ ADD (unambiguous)
```

### pathways.json
```diff
- "Rb",  ❌ REMOVE (conflicts with Rubidium)
+ "Rb protein",  ✅ ADD (more specific)
+ "retinoblastoma protein",  ✅ ADD (unambiguous)
```

---

## Testing Plan

After fixes:
1. Re-run scrape_pdfs_phase1.py
2. Verify "MS" no longer appears as indication
3. Verify "Ki" no longer appears as assay
4. Verify "Rb" no longer appears as pathway
5. Check entity coverage improves (target: ≥70%)
6. Verify top entities are meaningful

---

## Success Criteria

✅ **No false positives** for MS, Ki, Rb
✅ **Entity coverage** ≥70% (currently ~18% real)
✅ **Top 10 entities** are all valid (no ambiguous abbreviations)
✅ **Confidence distribution** improved (currently 93.9% low)

---

## Status

- [x] Diagnosis complete
- [ ] Emergency fix implemented
- [ ] Testing complete
- [ ] Production-ready

**Next Step**: Implement emergency fix to seed files and extraction logic.
