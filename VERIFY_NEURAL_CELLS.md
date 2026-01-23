# 🧪 Quick Verification Guide - Neural Cell Fixes

## Once Scraper Completes, Run These Commands:

### 1. Check for Duplicates (Most Important!)
```bash
python check_neural_cell_results.py
```

**Expected Output**:
```
✅ Neural Cell Entities Found:
   ✅ neuron
   ✅ neurons
   ✅ neuronal
   ✅ microglia
   ✅ microglial
   ✅ astrocyte
   ✅ astrocytes
   ✅ astrocytic
   ... (12 total)

✅ Comparison - Model Type Entities:
   ✅ No neural terms found as 'model' type (good!)
```

**If you see**: "⚠️ Found neural terms still typed as 'model'" → Something went wrong

---

### 2. Check Overlay Aliases
```bash
python -c "import json; data = json.load(open('output/run_meta_neuroscience_cognition.json')); print(f'Overlay aliases: {data.get(\"overlay_aliases_count\", 0)}')"
```

**Expected**: `Overlay aliases: 15-25` (was 0 before)

---

### 3. Check Top Entities
```bash
python -c "import json; data = json.load(open('output/run_meta_neuroscience_cognition.json')); print('Top 10 entities:'); [print(f'{i+1}. {e[\"entity_name\"]} ({e[\"entity_type\"]}): {e[\"event_count\"]} events') for i, e in enumerate(data['top_entities'][:10])]"
```

**Expected**: Neural cells (neuron, microglia, astrocyte) in top 10 with type="neural_cell"

---

### 4. Export Domain-Aware CSV
```bash
python export_csv_v5_domain_aware.py --domain neuroscience_cognition
```

**Expected**: Clean exports with neural_cell entities properly categorized

---

## Success Criteria ✅

- [ ] No neural cells in "model" type (check #1)
- [ ] Overlay aliases > 0 (check #2)
- [ ] Neural cells in top 10 (check #3)
- [ ] Clean exports generated (check #4)

---

## If All Checks Pass:

**You're done!** The neural cell promotion is complete and working correctly.

The system now:
- ✅ Treats neural cells as primary entities (not models)
- ✅ Normalizes variants (Neurons→neuron)
- ✅ Ranks neural cells correctly
- ✅ Maintains system honesty (still reports stem cells)

---

## If Any Check Fails:

1. Check which specific check failed
2. Review the error message
3. Check `NEURAL_CELL_FIXES_COMPLETE.md` for troubleshooting
4. Verify all 4 files were modified correctly:
   - seeds/neural_cells.json (41 terms)
   - seeds/overlays/neuroscience_overlay_v1.json (32 aliases)
   - scrape_pdfs_phase1.py (neural_cell extraction)
   - seeds/models.txt (neurons/astrocytes/microglia removed)

---

**Current Status**: ⏳ Scraper running (3/116 PDFs processed)  
**ETA**: ~15 minutes  
**Next Step**: Run verification commands above once complete
