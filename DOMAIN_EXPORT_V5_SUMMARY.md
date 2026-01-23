# 🎯 Domain-Aware Export v5 - Complete Implementation

## ✅ What Was Implemented

Successfully added **domain awareness** and **overlay alias normalization** to the export system, enabling Axon Labs to track which observational lens was used for each export.

---

## 🚀 Key Features

### 1. Domain Tracking Columns ✅

Every export now includes:
- **`domain_id`**: Domain identifier (e.g., `stem_cells_regen`, `neuroscience_cognition`)
- **`domain_name`**: Human-readable domain name (e.g., "Stem Cells & Regenerative Biology")
- **`overlay_id`**: Overlay version used (e.g., `stem_cells_regen_v1`)

**Example:**
```csv
event_id,domain,event_type,...,domain_id,domain_name,overlay_id
abc123,peptide,efficacy_signal,...,stem_cells_regen,Stem Cells & Regenerative Biology,stem_cells_regen_v1
```

### 2. Overlay Alias Normalization ✅

Entities are normalized using domain-specific aliases:
- **MSC** → **mesenchymal stem cell**
- **iPSC** → **induced pluripotent stem cell**
- **ESC** → **embryonic stem cell**
- **fMRI** → **functional magnetic resonance imaging**
- **mTOR** → **mechanistic target of rapamycin**

**Before (without overlay):**
```
Top entities:
1. MSC (stem_cell): 11 events
2. iPSC (stem_cell): 5 events
```

**After (with stem_cells_regen overlay):**
```
Top entities:
1. mesenchymal stem cell (stem_cell): 11 events
2. induced pluripotent stem cell (stem_cell): 5 events
```

### 3. All v4 Features Preserved ✅

- ✅ Process words demoted to context (quantification, chromatography, etc.)
- ✅ Safe confidence boost rule (objective criteria)
- ✅ Entity count columns (primary_entity_count, context_entity_count)
- ✅ run_meta.json for reproducibility

---

## 📁 Files Created/Modified

### New Files
1. **`export_csv_v5_domain_aware.py`** - Domain-aware export engine
2. **`test_domain_export.py`** - Verification test script
3. **`DOMAIN_EXPORT_V5_SUMMARY.md`** - This documentation

### Modified Files
4. **`entity_normalizer.py`** - Added `load_overlay_aliases()` function
   - Loads alias→canonical mappings from domain overlays
   - Prioritizes overlay aliases over core normalization
   - Supports MSC→mesenchymal stem cell, etc.

### Generated Exports (Example: stem_cells_regen domain)
5. **`output/events_export_stem_cells_regen.csv`** - 647 events with domain columns
6. **`output/candidates_primary_stem_cells_regen.csv`** - 107 entities with domain columns
7. **`output/run_meta_stem_cells_regen.json`** - Metadata tracking overlay usage

---

## 🎯 Usage Examples

### Export with Stem Cells Domain
```bash
python export_csv_v5_domain_aware.py --domain stem_cells_regen
```

**Output:**
```
✅ Exported domain-aware events: 647 → output\events_export_stem_cells_regen.csv
   Domain: Stem Cells & Regenerative Biology
   Overlay: stem_cells_regen_v1
   Aliases used: 16

Top entities (with normalization):
1. mesenchymal stem cell (stem_cell): 11 events  ← normalized from "MSC"
2. induced pluripotent stem cell (stem_cell): 5 events  ← normalized from "iPSC"
```

### Export with Neuroscience Domain
```bash
python export_csv_v5_domain_aware.py --domain neuroscience_cognition
```

### Export All Domains (No Filter)
```bash
python export_csv_v5_domain_aware.py
```

**Output:**
```
✅ Exported domain-aware events: 647 → output\events_export_v5.csv
   Domain: All Domains
   Overlay: None
   Aliases used: 0
```

---

## 📊 CSV Schema

### events_export_{domain}.csv

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `event_id` | string | Unique event identifier | `abc123...` |
| `domain` | string | Research domain | `peptide` |
| `event_type` | string | Event classification | `efficacy_signal` |
| `stage` | string | Study stage | `preclinical` |
| `outcome` | string | Outcome type | `positive` |
| `decision_driver` | string | Key decision factor | `efficacy` |
| `evidence_snippet` | string | Supporting text | `"MSC differentiation..."` |
| `confidence_original` | string | Original confidence | `med` |
| `confidence_boosted` | string | After boost rule | `high` |
| `primary_entity_count` | int | Count of research entities | `2` |
| `context_entity_count` | int | Count of experimental conditions | `1` |
| `entities_primary` | string | Research entities | `stem_cell:mesenchymal stem cell; assay:LC-MS` |
| `entities_context` | string | Experimental conditions | `model:IN VITRO` |
| `entities_all` | string | All entities combined | `stem_cell:mesenchymal stem cell; assay:LC-MS; model:IN VITRO` |
| **`domain_id`** | string | **Domain identifier** | **`stem_cells_regen`** |
| **`domain_name`** | string | **Domain display name** | **`Stem Cells & Regenerative Biology`** |
| **`overlay_id`** | string | **Overlay version** | **`stem_cells_regen_v1`** |
| `paper_id` | string | Source paper | `paper_001` |
| `created_at` | timestamp | Event timestamp | `2026-01-22 17:33:07` |

### candidates_primary_{domain}.csv

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `entity_type` | string | Entity category | `stem_cell` |
| `entity_name` | string | Canonical name (normalized) | `mesenchymal stem cell` |
| `entity_variant` | string | Entity variant | `cell_type` |
| `role` | string | Entity role | `primary` |
| `event_count` | int | Number of events | `11` |
| `paper_count` | int | Number of papers | `3` |
| `original_variants` | string | Original names found | `MSC; mesenchymal stem cell` |
| **`domain_id`** | string | **Domain identifier** | **`stem_cells_regen`** |
| **`domain_name`** | string | **Domain display name** | **`Stem Cells & Regenerative Biology`** |
| **`overlay_id`** | string | **Overlay version** | **`stem_cells_regen_v1`** |
| `first_seen` | timestamp | First occurrence | `2026-01-15 10:23:45` |
| `last_seen` | timestamp | Last occurrence | `2026-01-22 17:33:07` |

---

## 🔬 Technical Implementation

### Overlay Alias Loading

```python
from entity_normalizer import load_overlay_aliases

# Load stem cells overlay
aliases = load_overlay_aliases("stem_cells_regen")

# Returns:
{
    "msc": "mesenchymal stem cell",
    "ipsc": "induced pluripotent stem cell",
    "esc": "embryonic stem cell",
    "hsc": "hematopoietic stem cell",
    # ... 16 total aliases
}
```

### Normalization Priority

1. **Overlay aliases** (highest priority) - Domain-specific
2. **Core normalization map** - General variants
3. **Original name** (fallback) - If no mapping found

**Example:**
```python
# Input: "MSC"
# Check overlay: "msc" → "mesenchymal stem cell" ✅ (found)
# Output: "mesenchymal stem cell"

# Input: "mass spectrometry"
# Check overlay: not found
# Check core map: "mass spectrometry" → "LC-MS" ✅ (found)
# Output: "LC-MS"
```

### Domain Metadata Tracking

```json
{
  "run_id": "20260122_173307",
  "engine_version": "v5_domain_aware",
  "domain_id": "stem_cells_regen",
  "domain_name": "Stem Cells & Regenerative Biology",
  "overlay_id": "stem_cells_regen_v1",
  "overlay_aliases_count": 16,
  "counts": {
    "total_events": 647,
    "primary_entities": 107,
    "context_entities": 18
  }
}
```

---

## 🎯 Benefits for Axon Labs

### 1. Observational Lens Tracking
Every export shows **which domain lens was used**:
- Dashboard can display: "Viewing through: Stem Cells & Regenerative Biology lens"
- Users know the observational context
- Reproducible science - can recreate exact view

### 2. Clean Entity Names
Abbreviations normalized to full names:
- **MSC** → **mesenchymal stem cell** (more readable)
- **iPSC** → **induced pluripotent stem cell** (clearer)
- **fMRI** → **functional magnetic resonance imaging** (professional)

### 3. Domain-Specific Vocabulary
Each domain gets its own vocabulary without polluting others:
- Stem cells overlay: MSC, iPSC, SOX2, NANOG
- Neuroscience overlay: fMRI, optogenetics, hippocampus
- Longevity overlay: mTOR, AMPK, autophagy, senescence

### 4. Multi-Domain Comparison
Export same data through different lenses:
```bash
# Stem cells view
python export_csv_v5_domain_aware.py --domain stem_cells_regen

# Neuroscience view
python export_csv_v5_domain_aware.py --domain neuroscience_cognition

# Compare: same events, different entity emphasis
```

---

## 📊 Test Results

### Test: Domain Column Verification
```
✅ Total columns: 19 (includes domain_id, domain_name, overlay_id)
✅ Domain ID: 'stem_cells_regen'
✅ Domain Name: 'Stem Cells & Regenerative Biology'
✅ Overlay ID: 'stem_cells_regen_v1'
✅ Overlay Aliases: 16
```

### Test: Alias Normalization
```
Top 5 entities (with normalization):
1. LC-MS (assay): 85 events
2. AGGREGATION (pathway): 24 events
3. HPLC (assay): 19 events
4. mesenchymal stem cell (stem_cell): 11 events  ← normalized from "MSC"
5. SEMAGLUTIDE (compound): 10 events
```

**✅ Normalization working!** "MSC" was successfully normalized to "mesenchymal stem cell"

---

## 🔄 Integration with Existing System

### Backward Compatible
- v4 exports still work (no domain columns)
- v5 adds domain columns (optional)
- Core engine unchanged

### Drop-in Replacement
```python
# Old way (v4)
python export_csv_v4_professional.py

# New way (v5, no domain)
python export_csv_v5_domain_aware.py

# New way (v5, with domain)
python export_csv_v5_domain_aware.py --domain stem_cells_regen
```

### Database Schema
No database changes required:
- Domain columns added at export time
- Metadata stored in run_meta.json
- Overlay aliases loaded from JSON files

---

## 📚 Available Domains

| Domain ID | Domain Name | Overlay | Aliases |
|-----------|-------------|---------|---------|
| `stem_cells_regen` | Stem Cells & Regenerative Biology | stem_cells_overlay_v1.json | 16 |
| `neuroscience_cognition` | Neuroscience & Cognitive Science | neuroscience_overlay_v1.json | 12 |
| `biohacking_longevity` | Biohacking & Longevity Research | longevity_overlay_v1.json | 14 |
| `drug_discovery` | Drug Discovery & Development | (none yet) | 0 |
| `methods_tooling` | Methods & Analytical Tools | (none yet) | 0 |

---

## 🚀 Next Steps (Optional)

### 1. Add More Overlays
Create overlays for remaining domains:
- `drug_discovery_overlay_v1.json`
- `methods_tooling_overlay_v1.json`

### 2. Dashboard Integration
Use domain columns in Next.js dashboard:
```typescript
// Show which lens is active
<Badge>Viewing: {event.domain_name}</Badge>
<Badge variant="outline">{event.overlay_id}</Badge>

// Filter by domain
const stemCellEvents = events.filter(e => e.domain_id === 'stem_cells_regen')
```

### 3. Multi-Domain Comparison
Build comparison view:
```typescript
// Same event, different lenses
const stemCellView = exportWithDomain('stem_cells_regen')
const neuroView = exportWithDomain('neuroscience_cognition')

// Compare entity emphasis
```

---

## ✅ Summary

**Mission Accomplished:**
1. ✅ Domain tracking columns added (domain_id, domain_name, overlay_id)
2. ✅ Overlay alias normalization working (MSC→mesenchymal stem cell)
3. ✅ All v4 features preserved (process words, confidence boost, entity counts)
4. ✅ Backward compatible with existing exports
5. ✅ Tested and verified with stem_cells_regen domain
6. ✅ Ready for Axon Labs integration

**Files Ready:**
- `export_csv_v5_domain_aware.py` - Domain-aware export engine
- `entity_normalizer.py` - Enhanced with overlay alias support
- `test_domain_export.py` - Verification tests
- Domain-specific exports in `output/` directory

**Status:** 🎉 **PRODUCTION READY**

Axon Labs can now track which observational lens was used for each export, with clean entity normalization and full reproducibility.
