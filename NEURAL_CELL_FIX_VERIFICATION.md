# 🧠 Neural Cell Fix - Verification Plan

## Current Status: ⏳ SCRAPER RUNNING

The scraper is now running with the updated code that includes neural_cell extraction.

**Evidence it's working**:
```
📋 Loaded JSON seeds:
   Assays: 129
   Pathways: 124
   Indications: 83
   Neural Cells: 41  ✅ ← NEW! This confirms neural_cells.json is loaded
```

**Processing**: 116 PDFs from neuroscience_v1 corpus  
**Expected time**: 15-20 minutes

---

## What Changed

### Before (v2 run):
```python
# Neurons/Microglia/Astrocytes extracted as MODEL type
for model in MODEL_SEED_LIST:
    if re.search(r'\b' + re.escape(model) + r'\b', s_l):
        ents.append({
            "entity_type": "model",  # ❌ Wrong!
            "entity_name": name,
            "role": "model"
        })
```

### After (v3 run - current):
```python
# Neural cells extracted as NEURAL_CELL type (step 6)
neural_cells_data = SEEDS.get("neural_cells", {})
for neural_cell in neural_cells_data.get("neural_cells", []):
    if re.search(r'\b' + re.escape(neural_cell.lower()) + r'\b', s_l):
        ents.append({
            "entity_type": "neural_cell",  # ✅ Correct!
            "entity_name": neural_cell,
            "role": "tested"  # PRIMARY entity
        })
```

---

## Expected Results

### Top Entities - Before (v2):
```
#3: stem cell (382 events) - stem_cell type
#4: organoid (344 events) - stem_cell type
#6: differentiation (263 events) - stem_cell type
#8: Neurons (208 events) - model type ❌
#11: Microglia (189 events) - model type ❌
#16: Astrocytes (148 events) - model type ❌
```

### Top Entities - After (v3 - Expected):
```
#1-3: neuron (208+ events) - neural_cell type ✅
#4-6: microglia (189+ events) - neural_cell type ✅
#7-9: astrocyte (148+ events) - neural_cell type ✅
#10-12: stem cell (382 events) - stem_cell type
#13-15: organoid (344 events) - stem_cell type
```

**Key changes**:
- Neural cells will rank HIGHER (primary entities prioritized)
- Neural cells will have type="neural_cell" not "model"
- Overlay aliases should be >0 (normalization working)

---

## Verification Checklist

Once scraper completes, verify:

### ✅ Step 1: Check Entity Types
```bash
# Read metadata
cat output/run_meta_neuroscience_cognition.json

# Look for:
# - "type": "neural_cell" (not "model")
# - overlay_aliases_count > 0 (not 0)
```


### ✅ Step 2: Check Top Entities
Expected to see:
- neuron, microglia, astrocyte in top 10
- All with type="neural_cell"
- All with role="tested"

### ✅ Step 3: Check Overlay Aliases
Expected:
- overlay_aliases_count: 15-25 (was 0)
- Aliases like: Neurons→neuron, Microglia→microglia, etc.

### ✅ Step 4: Check Entity Distribution
```bash
# Count by type
python -c "
import sqlite3
con = sqlite3.connect('output/peptide_intel.sqlite')
cur = con.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type')
for row in cur:
    print(f'{row[0]}: {row[1]}')
"
```

Expected to see:
- neural_cell: 10-20 unique entities
- stem_cell: 8-12 unique entities
- model: 50-80 unique entities (reduced from before)

---

## Success Criteria

| Metric | Before | Target | Status |
|--------|--------|--------|--------|
| **Neural cell type** | model | neural_cell | ⏳ |
| **Neural cell rank** | #8, #11, #16 | Top 10 | ⏳ |
| **Overlay aliases** | 0 | 15-25 | ⏳ |
| **Entity role** | model | primary | ⏳ |
| **System honesty** | ✅ | ✅ | ⏳ |

---

## What This Proves

### If Successful ✅
- Neural cells are correctly identified as PRIMARY research entities
- Overlay normalization is working (aliases >0)
- System still honestly reports stem cell presence
- Rankings reflect research focus (neural cells) vs infrastructure (stem cells)

### If Unsuccessful ❌
- Need to debug why neural_cell extraction isn't working
- Check if neural cell terms are actually in the PDFs
- Verify word boundary matching is correct

---

## Next Steps After Verification

1. **If successful**: Export and document final results
2. **If unsuccessful**: Debug and fix extraction logic
3. **Either way**: Create final summary for user

---

**Status**: ⏳ Waiting for scraper to complete (15-20 minutes)  
**Files to check**: 
- `output/run_meta_neuroscience_cognition.json`
- `output/candidates_primary_neuroscience_cognition.csv`
- `output/peptide_intel.sqlite`
