# Production Blockers - Analysis & Action Plan

## Current State Assessment

### ✅ What's Working
1. **Event extraction**: 640 events consistently produced
2. **Table structure**: Correct columns (domain, event_type, stage, outcome, decision, snippet, confidence)
3. **Entity rollup**: Candidates table with counts, papers, time ranges
4. **Fix B implemented**: Generic models (HUMAN, SERUM, RAT) split into metadata columns

### ❌ Critical Blockers (Priority Order)

## BLOCKER 1: Entities Missing 87% of Time ⚠️ CRITICAL

**Problem**: 
- `entities` column empty in ~87% of events (557/640)
- `tags` column empty in ~72% of events (461/640)
- Makes dashboard filters useless

**Root Cause**:
- Entity extraction too conservative
- Not linking entities to events properly
- Missing entity types (assays, pathways, indications)

**Fix Required**:
```python
# Current: Only extracts if perfect match
# Needed: Extract compound OR model OR assay OR target per event

Target: ≥70% of events have ≥1 entity
```

**Action Items**:
1. ✅ Add assay/method extraction (LC-MS, HPLC, ELISA, etc.)
2. ✅ Add pathway extraction (mTOR, AMPK, PI3K, etc.)
3. ✅ Improve entity-event linking logic
4. ✅ Lower extraction thresholds for high-signal contexts

---

## BLOCKER 2: Top Entities Too Generic ⚠️ HIGH PRIORITY

**Problem**:
```
Current Top 10:
1. HUMAN (generic) ❌
2. SERUM (generic) ❌
3. Plasma (generic) ❌
4. RAT (generic) ❌
5. BLOOD (generic) ❌
6. MSC (useful) ✅
7. SEMAGLUTIDE (useful) ✅
...
```

**Desired Top 10**:
```
1. SEMAGLUTIDE (compound) ✅
2. MSC (stem cell) ✅
3. GLP1R (target) ✅
4. LC-MS/MS (assay) ✅
5. GLUCAGON (compound) ✅
6. organoid (model) ✅
7. COX2 (target) ✅
...
```

**Fix Required**:
- ✅ **Already implemented in export_csv_v2.py** (Fix B)
- Generic models filtered to metadata columns
- Only headline entities in candidates_export.csv

**Status**: ✅ FIXED (need to verify it's being used)

---

## BLOCKER 3: Confidence Too Low (94.5% Low) ⚠️ MEDIUM PRIORITY

**Problem**:
```
Current Distribution:
- Low: 605/640 (94.5%) ❌
- Med: 34/640 (5.3%)
- High: 1/640 (0.2%)
```

**Desired Distribution**:
```
Target:
- Low: 40% (256 events)
- Med: 45% (288 events)
- High: 15% (96 events)
```

**Root Cause**:
- Scoring too strict
- Not using multi-signal detection
- Missing evidence signals (quantitative data, specific methods, etc.)

**Fix Required**:
```python
# Add promotion rules:
# 2+ high-signal terms (LC-MS + in vivo) → med
# 3+ signals + specific compound/target → high
# Quantitative data (IC50, EC50, half-life) → +1 level
```

**Action Items**:
1. Add multi-signal boost
2. Detect quantitative measurements
3. Promote events with specific entities + methods
4. Adjust thresholds (currently too high)

---

## BLOCKER 4: Domain Too Narrow (100% Peptide) ⚠️ LOW PRIORITY

**Problem**:
- All 640 events tagged "peptide"
- No stem cell, oncology, or other domains

**Fix Required**:
- Run with stem_cell seeds
- Add domain detection logic
- Support multi-domain papers

**Status**: Lower priority (can be addressed after Blockers 1-3)

---

## Success Metrics (Lab-Demo-Ready)

When these are true, system is production-ready:

1. ✅ **Entities present in ≥70% of events** (currently 13%)
2. ✅ **Confidence spread**: 40% low, 45% med, 15% high (currently 94.5% low)
3. ✅ **Top entities include real items**: SEMAGLUTIDE, MSC, GLP1R, LC-MS/MS, organoid (not just SERUM/HUMAN)
4. ✅ **Filterable by**: compound, target, model, stage, assay

---

## Recommended Implementation Order

### Phase 1: Fix Entity Coverage (BLOCKER 1) - CRITICAL
**Goal**: 13% → 70% entity coverage

1. Add assay/method seed list (LC-MS, HPLC, ELISA, Western blot, etc.)
2. Add pathway seed list (mTOR, AMPK, PI3K, MAPK, etc.)
3. Improve entity-event linking (lower thresholds in high-signal contexts)
4. Add indication extraction (diabetes, cancer, inflammation, etc.)

**Expected Impact**: 
- Entities in 70%+ of events
- Dashboard filters become useful
- Better research intelligence

### Phase 2: Verify Fix B is Active (BLOCKER 2) - HIGH
**Goal**: Ensure generic models filtered from top entities

1. Confirm export_csv_v2.py is being used (not export_csv.py)
2. Verify candidates_export.csv shows only headline entities
3. Check events_export.csv has separate metadata columns

**Expected Impact**:
- Top 10 entities are meaningful
- Generic models in metadata only
- Better entity rankings

### Phase 3: Improve Confidence (BLOCKER 3) - MEDIUM
**Goal**: 94.5% low → 40% low, 45% med, 15% high

1. Add multi-signal detection
2. Promote events with quantitative data
3. Boost events with specific entities + methods
4. Adjust thresholds

**Expected Impact**:
- Better confidence distribution
- High-confidence events are truly high-value
- Easier to prioritize research

### Phase 4: Domain Expansion (BLOCKER 4) - LOW
**Goal**: Support multi-domain research

1. Run with stem_cell seeds
2. Add domain detection logic
3. Support papers covering multiple domains

**Expected Impact**:
- Broader research coverage
- Multi-domain intelligence

---

## Current Status

- ✅ Fix B implemented (generic models split)
- ❌ Blocker 1 not addressed (87% missing entities)
- ❌ Blocker 3 not addressed (94.5% low confidence)
- ❌ Blocker 4 not addressed (100% peptide domain)

**Next Step**: Implement Phase 1 (Fix Entity Coverage) to achieve lab-demo-ready quality.
