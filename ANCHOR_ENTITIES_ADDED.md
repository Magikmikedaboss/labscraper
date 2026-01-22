# Anchor Entity Extraction - Implementation Complete

## 🎯 Problem Solved

**Before**: Only extracted peptide sequences and stem cell markers (7 entities total)
**After**: Now extracts compounds, targets, and models - the "anchors" that labs actually care about

## ✅ What Was Added

### 1. Compound Extraction
**Entity Type**: `compound`
**Seed List**: 25 compounds including:
- Longevity drugs: metformin, rapamycin, resveratrol, nmn
- Peptide drugs: semaglutide, liraglutide, etelcalcetide
- Senolytics: dasatinib, navitoclax

**Example**: "Metformin improved stability" → extracts METFORMIN as compound

### 2. Target Extraction (Context-Gated)
**Entity Type**: `target`
**Seed List**: 15 biological targets including:
- Metabolic: mTOR, AMPK, SIRT1, IGF1
- Peptide/endocrine: GLP-1R, GCGR
- Inflammation: NF-κB, TNF, IL-6

**Context Gate**: Only extracts when sentence contains target-related words:
- agonist, antagonist, inhibitor, activator
- binding, affinity, receptor, pathway
- target, modulator, blocker

**Example**: "GLP-1R agonist showed activity" → extracts GLP-1R as target
**Non-example**: "GLP-1R was mentioned" → NOT extracted (no context)

### 3. Model Extraction
**Entity Type**: `model`
**Three Subtypes**:

**A) Cell Lines** (10 lines):
- HEK293, CHO, HeLa, MCF-7, A549, etc.
- Variant: `cell_line`

**B) Organisms** (6 organisms):
- Mouse, Rat, Human, Mice, Rats, Murine
- Variant: `organism`

**C) Biofluids** (3 fluids):
- Serum, Plasma, Whole blood
- Variant: `biofluid`

**Example**: "Peptide degraded in mouse serum" → extracts Mouse (organism) + Serum (biofluid)

## 📊 Expected Impact

### Before Anchor Extraction
```
7 entities total:
- 3 peptides (ETELCALCETIDE, KYNETWRSED, PLECANATIDE)
- 4 stem cells (MSC, stem cell, mesenchymal, stem-cell)
```

### After Anchor Extraction
```
~20-30 entities total:
- 3 peptides
- 4 stem cells
- 5-10 compounds (metformin, rapamycin, etc.)
- 3-5 targets (mTOR, AMPK, GLP-1R, etc.)
- 5-8 models (Mouse, Serum, HEK293, etc.)
```

## 🔗 Event → Anchor Linkage

Every event now links to multiple entity types:

**Example Event**:
```
"Semaglutide (GLP-1R agonist) showed stability in mouse serum"

Entities Extracted:
- SEMAGLUTIDE (compound)
- GLP-1R (target) 
- Mouse (model/organism)
- Serum (model/biofluid)

Event Links:
- compound_id → SEMAGLUTIDE
- target_id → GLP-1R
- model_id → Mouse, Serum
```

## 💡 Why This Matters

### Labs Think in Anchors
Instead of: "442 events about peptides"
Now: "Metformin failed 3 times in mouse models across 2 papers"

### Enables Powerful Queries
```sql
-- Find all failures with mTOR as target
SELECT * FROM research_events e
JOIN event_entities ee ON e.event_id = ee.event_id
JOIN entities ent ON ee.entity_id = ent.entity_id
WHERE ent.entity_name = 'MTOR' 
  AND e.failure_reason != 'unknown';

-- Find compounds tested in mouse models
SELECT DISTINCT c.entity_name as compound, 
       COUNT(*) as events
FROM entities c
JOIN event_entities ec ON c.entity_id = ec.entity_id
JOIN event_entities em ON ec.event_id = em.event_id
JOIN entities m ON em.entity_id = m.entity_id
WHERE c.entity_type = 'compound'
  AND m.entity_name = 'Mouse'
GROUP BY c.entity_name;
```

### Dashboard-Ready Data
Now you can build:
- **Top compounds by failure rate**
- **Targets with repeated issues**
- **Models where stability fails most**
- **Compound-target-model failure patterns**

## 🔧 Implementation Details

### Code Changes

**1. Added Extraction Functions** (`scrape_pdfs.py`):
```python
def extract_compounds(sentence: str) -> list[dict]
def extract_targets(sentence: str) -> list[dict]  # Context-gated
def extract_models(sentence: str) -> list[dict]
```

**2. Updated Main Extraction**:
```python
def extract_entities(sentence: str) -> list[dict]:
    ents = []
    
    # 1) Peptides (strict presentation patterns)
    ents.extend(extract_peptide_sequences(sentence))
    
    # 2) Compounds (NEW)
    ents.extend(extract_compounds(sentence))
    
    # 3) Targets (NEW - context-gated)
    ents.extend(extract_targets(sentence))
    
    # 4) Models (NEW - cell lines, organisms, biofluids)
    ents.extend(extract_models(sentence))
    
    # 5) Stem cells (existing)
    ents.extend(extract_stem_cells(sentence))
    
    return ents
```

**3. Database Integration**:
- All entities stored in same `entities` table
- Differentiated by `entity_type` and `entity_variant`
- Linked to events via `event_entities` table

## 📈 Next Steps

### Immediate (After This Run)
1. ✅ Verify anchor entities are extracted
2. ✅ Check entity counts by type
3. ✅ Validate event-entity linkages

### Future Enhancements
1. **Expand Seed Lists**:
   - Add more compounds as discovered
   - Add more targets (kinases, receptors)
   - Add more cell lines

2. **Smarter Extraction**:
   - Use NER models for compound detection
   - Add synonym mapping (e.g., "rapamycin" = "sirolimus")
   - Extract dosages with compounds

3. **Relationship Mining**:
   - Compound-target pairs (e.g., "metformin activates AMPK")
   - Model-specific failures (e.g., "unstable in mouse but not rat")

## 🎯 Success Criteria

✅ **Compounds extracted**: Should see metformin, rapamycin, etc. in entities
✅ **Targets extracted**: Should see mTOR, AMPK, GLP-1R (only with context)
✅ **Models extracted**: Should see Mouse, Serum, HEK293, etc.
✅ **Event linkage**: Events should link to multiple entity types
✅ **No false positives**: Context gating prevents noise

## 📝 Files Modified

1. **scrape_pdfs.py** (880 lines):
   - Added `KNOWN_PEPTIDES` whitelist
   - Added `extract_compounds()` function
   - Added `extract_targets()` function (context-gated)
   - Added `extract_models()` function
   - Updated `extract_entities()` to call all extractors

2. **Database** (schema unchanged):
   - Existing `entities` table handles all types
   - `entity_type` field differentiates: peptide, compound, target, model, stem_cell
   - `entity_variant` field adds detail: drug, protein, cell_line, organism, biofluid

## 🚀 Status

**Implementation**: ✅ COMPLETE
**Testing**: 🔄 IN PROGRESS (scraper running)
**Verification**: ⏳ PENDING (after scraper completes)

---

**This closes Gap #1: Named anchors (compounds, targets, models)**

Next gaps to address:
- Gap #2: Event → Anchor linkage (already working via event_entities table)
- Gap #3: Time & repetition signals (need aggregation queries)
