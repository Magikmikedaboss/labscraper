# Dual-Lens Overlay System Guide

## Overview

The biohacking_longevity domain now supports **dual-lens analysis** using two complementary overlays:

1. **Science Research Lens** - Emphasizes rigorous research, mechanisms, replication
- **Base Seeds**: compounds.txt, targets.txt, models.txt, assays.json, etc.
- **Purpose**: Entity extraction (what exists)
- **Purpose**: Emphasis and ranking (what matters)
- **Result**: Different "views" of the same data

---
- Mechanistic pathways (mTOR, autophagy, senescence)
- Experimental rigor (in vivo, controlled, randomized)
**What It De-emphasizes:**
- Anecdotal reports
- Self-reported outcomes

**Boost Terms:**
```text
mechanism: +3
pathway: +3
replication: +4
clinical trial: +4
in vivo: +3
statistically significant: +3
```

**Demote Terms:**
```text
anecdotal: -2
self-reported: -2
stack: -1
biohack: -1
```

**Priority Entities:**
- Pathways: 2x
- Assays: 2x
- Models: 2x
- Indications: 2x
- Compounds: 1x

**Pattern Bias:**
- Convergence: 1.5x (values research agreement)
- Replication: 2.0x (highly values repeated findings)
- Fragmentation: 0.8x (devalues scattered results)

---

### Biohacking Curiosity Lens (`biohacking_curiosity_v1`)

**What It Emphasizes:**
- Protocols and dosing strategies
- Stacks and supplement combinations
- Performance outcomes (sleep, energy, focus, cognition)
- Self-experimentation language
- Tracking and biomarkers (HRV, glucose, VO2 max)
- Anti-aging and longevity optimization

**What It De-emphasizes:**
- In vitro studies
- Cell line research
- Molecular mechanisms
- Rodent models

**Boost Terms:**
```text
protocol: +3
stack: +3
self-experiment: +3
anti-aging: +3
dosage: +2
optimization: +2
sleep/energy/focus/cognition: +2
```

**Demote Terms:**
```text
in vitro: -1
cell line: -1
rodent model: -1
pathway: -1
molecular mechanism: -1
```

**Priority Entities:**
- Compounds: 2x
- Indications: 2x
- Models: 1x
- Pathways: 1x
- Assays: 0.5x

**Pattern Bias:**
- Escalation: 1.5x (values growing interest)
- Fragmentation: 1.2x (tolerates diverse approaches)
- Convergence: 0.8x (less emphasis on consensus)

---

## Operating Modes

### Option A: Single Lens Per Run (Config-Based)

Set a single overlay in the domain config, then run ingestion:

### Science View
```bash
python utils/run_engine.py \
  --input-dir input/pdfs/biohacking_longevity \
  --domain biohacking_longevity
```

### Curiosity View
```bash
python utils/run_engine.py \
  --input-dir input/pdfs/biohacking_longevity \
  --domain biohacking_longevity
```

**Result:** Two separate runs, two different rankings

---

### Option B: Dual Lens (Recommended - Current Setup)

The domain file is configured for dual-lens mode:

```json
"overlays": [
  "science_research_v1",
  "biohacking_curiosity_v1"
]
```

**Single Run:**
```bash
python utils/run_engine.py \
  --input-dir input_pdfs/longevity_v1 \
  --domain biohacking_longevity
```

**Result:** One run, dual scoring in output files

---

## Output Files (Dual-Lens Mode)

### events.csv
Same events, but with dual scores:
```csv
event_id,evidence_snippet,confidence_science,confidence_curiosity,...
```

### entities.csv
Same entities, but with dual rankings:
```csv
entity_name,rank_science,rank_curiosity,score_science,score_curiosity,...
```

### patterns.csv
Same patterns, but with dual emphasis:
```csv
pattern_type,score_science,score_curiosity,bucket_science,bucket_curiosity,...
```

---

## Example: Same Data, Different Stories

### Input Document
> "Metformin activates AMPK pathway in mouse models, showing dose-dependent lifespan extension. 
> Human trials report improved glucose control and energy levels with 500mg daily protocol."

### Science Lens Output
**Top Entities:**
1. AMPK pathway (mechanism)
2. Mouse model (in vivo)
3. Dose-dependent (rigor)
4. Clinical trial (translational)

**Confidence:** HIGH (mechanism + model + dose-response)

### Curiosity Lens Output
**Top Entities:**
1. Metformin (compound)
2. 500mg daily (protocol/dosage)
3. Energy levels (performance outcome)
4. Glucose control (biomarker)

**Confidence:** HIGH (compound + dosage + outcome)

---

## What Overlays DO NOT Do

 **Do NOT change extraction**
- Same entities are found regardless of overlay
- No hallucination of new entities
- No hiding of evidence

 **Do NOT filter documents**
- All documents are processed
- All events are captured

 **DO change emphasis**
- Boost/demote confidence scores
- Reorder entity rankings
- Bias pattern scoring
- Influence what rises to "top 20"

---

## Use Cases

### For Researchers (Science Lens)
- "Show me mechanistic convergence around mTOR inhibition"
- "What pathways have replication across independent cohorts?"
- "Which compounds have clinical trial momentum?"

### For Biohackers (Curiosity Lens)
- "What protocols are people experimenting with?"
- "Which stacks mention sleep and cognition?"
- "What dosages appear in self-experimentation reports?"

### For Product Teams (Both Lenses)
- Toggle between views in UI
- "Research View" vs "Explorer View"
- Compare what scientists emphasize vs what practitioners try

---

## Configuration Files

### Domain File
`config/domains/biohacking_longevity.json`
```json
{
  "id": "biohacking_longevity",
  "overlays": [
    "science_research_v1",
    "biohacking_curiosity_v1"
  ]
}
```

### Overlay Files
- `seeds/overlays/science_research_v1.json`
- `seeds/overlays/biohacking_curiosity_v1.json`

---

## Testing the Overlays

### Quick Test (Single Lens)
```bash
# Set science overlay only in domain config, then run:
python utils/run_engine.py \
  --input-dir input/pdfs/biohacking_longevity \
  --domain biohacking_longevity \
  --output-db output/test_science_lens.sqlite

# Set curiosity overlay only in domain config, then run:
python utils/run_engine.py \
  --input-dir input/pdfs/biohacking_longevity \
  --domain biohacking_longevity \
  --output-db output/test_curiosity_lens.sqlite
```

### Compare Results
```python
# Compare top entities between lenses
import sqlite3

con_sci = sqlite3.connect('output/test_science_lens.sqlite')
con_cur = sqlite3.connect('output/test_curiosity_lens.sqlite')

# Get top 20 from each
# Compare rankings
# Analyze differences
```

---

## Next Steps

1. **Test on small corpus** - Validate overlays work as expected
2. **Compare outputs** - Verify different emphasis patterns
3. **Tune weights** - Adjust boost/demote values if needed
4. **Full production run** - Apply to complete corpus
5. **UI integration** - Add toggle between views

---

## Key Principles

1. **Base seeds = reality** (what exists)
2. **Overlays = perspective** (what matters)
3. **Multiple overlays = multiple stories** (same facts, different emphasis)
4. **No data loss** (all evidence preserved)
5. **User choice** (toggle between views)

The system doesn't change what's true; it changes what you notice first.


