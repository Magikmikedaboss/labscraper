# Output Directory - Production Data

This directory contains the production-ready database and normalized CSV exports.

---

## Files

### Database
- **`peptide_intel.sqlite`** - Main production database
  - 647 research events
  - 137 unique entities (125 after normalization)
  - Clean data (0% false positives)

### CSV Exports (Normalized)

#### For Dashboards & Rankings
- **`candidates_primary.csv`** - 114 primary entities
  - Use for: Top entities charts, trend analysis, research focus areas
  - Excludes: Context entities (in vivo, serum, etc.)
  - Includes: Consolidated variants (LC-MS includes mass spectrometry, LC-MS/MS, etc.)

#### For Filters & Facets
- **`candidates_context.csv`** - 11 context entities
  - Use for: Filter dropdowns, experimental condition facets
  - Includes: in vivo, in vitro, serum, plasma, human, rat, etc.
  - Purpose: Filtering only, not for rankings

#### Combined Data
- **`candidates_export_v3.csv`** - All 125 entities (primary + context)
  - Use for: Complete entity analysis
  - Includes: Role classification (primary vs context)

- **`events_export_v3.csv`** - All 647 events with normalized entities
  - Use for: Event-level analysis
  - Columns:
    - `entities_primary`: Research entities only (for analysis)
    - `entities_context`: Experimental context (for filtering)
    - `entities_all`: Everything combined

---

## Data Quality

### Entity Normalization
Variants are automatically consolidated:
- **LC-MS** (85 events) ← LC-MS, LC-MS/MS, mass spectrometry, mass spectrometer, QTOF, triple quadrupole
- **HPLC** (19 events) ← HPLC, RP-HPLC, liquid chromatography
- **QUANTIFICATION** (16 events) ← quantification, quantitation
- **PURIFICATION** (10 events) ← SPE, purification
- **ALZHEIMER** (6 events) ← Alzheimer, Alzheimer's disease

### Top 10 Primary Entities
1. LC-MS (assay): 85 events
2. AGGREGATION (pathway): 24 events
3. HPLC (assay): 19 events
4. QUANTIFICATION (assay): 16 events
5. CHROMATOGRAPHY (assay): 15 events
6. MSC (stem_cell): 11 events
7. SEMAGLUTIDE (compound): 10 events
8. PURIFICATION (assay): 10 events
9. PEPTIDE DEGRADATION (pathway): 9 events
10. KINASE (target): 8 events

### Context Entities (Demoted from Rankings)
- HUMAN, SERUM, PLASMA, IN VIVO, FBS, RAT, CELL CULTURE, TISSUE, IN VITRO, BLOOD

---

## Usage Examples

### Dashboard: Top Entities Chart
```python
import pandas as pd

# Load primary entities only
df = pd.read_csv('candidates_primary.csv')

# Sort by event count
top_20 = df.nlargest(20, 'event_count')

# Display
print(top_20[['entity_name', 'entity_type', 'event_count']])
```

### Filter: Experimental Conditions
```python
# Load context entities for filters
context = pd.read_csv('candidates_context.csv')

# Get unique experimental conditions
conditions = context[context['entity_type'] == 'model']['entity_name'].tolist()
# ['HUMAN', 'SERUM', 'PLASMA', 'IN VIVO', 'FBS', 'RAT', 'CELL CULTURE', 'TISSUE', 'IN VITRO', 'BLOOD']
```

### Analysis: Events with Specific Entity
```python
# Load events
events = pd.read_csv('events_export_v3.csv')

# Find events mentioning LC-MS
lcms_events = events[events['entities_primary'].str.contains('LC-MS', na=False)]

print(f"Found {len(lcms_events)} events using LC-MS")
```

---

## Regenerating Exports

To regenerate the CSV exports from the database:

```bash
python export_csv_v3.py
```

This will:
1. Load the normalization map from `seeds/normalization.json`
2. Consolidate entity variants
3. Classify entities as primary or context
4. Export to the 4 CSV files

---

## Data Freshness

- **Last Updated**: 2026-01-22
- **Source PDFs**: 19 peptide research papers
- **Events Extracted**: 647
- **Entity Coverage**: 41.4% (268/647 events have entities)
- **False Positive Rate**: 0%

---

## Notes

- All entity names are normalized to canonical forms
- Original variant names are preserved in the `original_variants` column
- Context entities are excluded from rankings but available for filtering
- Database schema defined in `../schema.sql`
