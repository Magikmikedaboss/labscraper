# ✅ Seed Overlay System Implemented

## What Was Built

A **domain-specific vocabulary system** that adds specialized terms on top of core seeds without polluting the base vocabulary or causing false positives.

---

## The Three-Layer Architecture

### 🧱 Layer 1: The Engine (Never Changes)
- Extracts events from papers
- Identifies entities
- Detects patterns (convergence, escalation, stagnation, fragmentation, abandonment)
- Assigns momentum-style scores
- **Domain-agnostic**: Only sees research behavior, not field-specific meaning

### 🔍 Layer 2: Domains (How Humans Look at the Engine)
- **Lens, not rewrite**: Same data, different interpretation
- Controls pattern emphasis (soft multipliers 0.9-1.25x)
- Defines language guardrails (allowed/forbidden phrases)
- Specifies preferred entity types
- **5 domains**: Biohacking, Stem Cells, Neuroscience, Drug Discovery, Methods

### 🧬 Layer 3: Seed Files (What the Engine Can Recognize)
- **Core seeds**: Always loaded (assays, pathways, indications, models, targets, compounds)
- **Overlay seeds**: Optional domain-specific vocabulary
- **Safe expansion**: Adds terms only when domain is active
- **Prevents pollution**: Avoids false positives from irrelevant terms

---

## Files Created

### Overlay Seed Files (3 overlays)
1. ✅ `seeds/overlays/stem_cells_overlay_v1.json` - Stem cell vocabulary
2. ✅ `seeds/overlays/neuroscience_overlay_v1.json` - Neuroscience vocabulary
3. ✅ `seeds/overlays/longevity_overlay_v1.json` - Longevity/aging vocabulary

### Python Infrastructure
4. ✅ `seed_overlay_loader.py` - Overlay loader with merge logic

### Documentation
5. ✅ `SEED_OVERLAYS_IMPLEMENTED.md` - This file

---

## Overlay Contents

### 1. Stem Cells Overlay (`stem_cells_overlay_v1.json`)

**Purpose**: Boost recognition of stem cell models, markers, and translational barriers

**Categories**:
- **Cell Types** (8 terms): mesenchymal stem cell, iPSC, ESC, NSC, HSC, etc.
- **Aliases**: MSC→mesenchymal stem cell, iPSC→induced pluripotent stem cell
- **Processes** (11 terms): differentiation, reprogramming, pluripotency, engraftment
- **Models** (9 terms): organoid, spheroid, 3D culture, xenograft, patient-derived organoid
- **Markers** (15 terms): SOX2, NANOG, OCT4, CD73, CD90, CD105, etc.
- **Barriers** (8 terms): tumorigenicity, heterogeneity, poor engraftment, immune rejection

**Exclusions**: stem cell clinic, stem cell spa, miracle cure, guaranteed results

**Why it works**:
- Captures translational friction terms (engraftment, heterogeneity) → improves stagnation detection
- Includes aliases but anchors to full names → prevents MS/Ki-style crashes
- Focuses on research barriers, not marketing hype

---

### 2. Neuroscience Overlay (`neuroscience_overlay_v1.json`)

**Purpose**: Capture model diversity and method fragmentation in neuroscience

**Categories**:
- **Brain Regions** (8 terms): hippocampus, prefrontal cortex, amygdala, striatum
- **Cell Types** (7 terms): neuron, astrocyte, microglia, oligodendrocyte
- **Processes** (8 terms): synaptic plasticity, LTP, LTD, neuroinflammation, myelination
- **Methods** (14 terms): electrophysiology, patch clamp, calcium imaging, fMRI, EEG, optogenetics
- **Diseases** (9 terms): Alzheimer's, Parkinson's, ALS, epilepsy, schizophrenia
- **Biomarkers** (7 terms): amyloid beta, tau, alpha-synuclein, BDNF, GFAP

**Exclusions**: nootropic stack, supplement stack, buy now, coupon

**Why it works**:
- Neuroscience is extremely fragmented → these terms help measure fragmentation, not guess it
- Method diversity (electrophysiology, imaging, optogenetics) → improves method convergence detection
- Disease terms anchor to canonical neurodegenerative conditions

---

### 3. Longevity Overlay (`longevity_overlay_v1.json`)

**Purpose**: Anchor to aging hallmarks and measurement trends

**Categories**:
- **Hallmarks** (11 terms): autophagy, cellular senescence, mitochondrial dysfunction, proteostasis
- **Pathways** (9 terms): mTOR, AMPK, sirtuin, NAD+, FOXO, IGF-1, insulin signaling
- **Measurements** (8 terms): epigenetic clock, DNA methylation age, proteomics, metabolomics
- **Interventions** (8 terms): caloric restriction, fasting, rapamycin, metformin, senolytics
- **Models** (5 terms): C. elegans, Drosophila, zebrafish, mouse model
- **Barriers** (4 terms): translation to humans, species differences, confounding

**Exclusions**: supplement, proprietary blend, biohacking store, affiliate link

**Why it works**:
- Longevity is measurement-heavy → captures omics/clocks trend
- Anchors to canonical aging hallmarks (López-Otín et al. 2013)
- Includes intervention terms but filters marketing language

---

## How Overlays Work

### Loading Logic

```python
from seed_overlay_loader import load_seeds_with_overlay

# Load core seeds only (no overlay)
seeds = load_seeds_with_overlay()

# Load core + stem cells overlay
seeds = load_seeds_with_overlay("stem_cells_regen")

# Load core + neuroscience overlay
seeds = load_seeds_with_overlay("neuroscience_cognition")

# Load core + longevity overlay
seeds = load_seeds_with_overlay("biohacking_longevity")
```

### Merge Strategy

**Conservative merge** (prevents pollution):
1. Core seeds always loaded first
2. Overlay adds new categories (e.g., `cell_types`, `brain_regions`)
3. If category exists in both, lists are combined and deduplicated
4. Base values never overwritten
5. Overlay metadata tracked (`_overlay_id`, `_overlay_domain`)

### Safety Rules

✅ **Abbreviations must have full forms**
- ✅ Good: `"aliases": {"mesenchymal stem cell": ["MSC", "MSCs"]}`
- ❌ Bad: Adding "MSC" directly to entity list

✅ **Avoid ambiguous short terms**
- ✅ Good: "induced pluripotent stem cell", "iPSC" as alias
- ❌ Bad: "Ki", "MS", "Rb" (learned from crash)

✅ **Filter marketing language**
- ✅ Good: Exclusions list filters "supplement", "coupon", "miracle"
- ❌ Bad: Allowing consumer marketing terms as entities

---

## Testing Results

```bash
$ python seed_overlay_loader.py
```

**Output**:
```
SEED OVERLAY LOADER - TESTING
======================================================================

1. Loading core seeds (no overlay)...
   ✅ Loaded 9 core seed categories
      - assays: 4 categories
      - compounds: 52 items
      - indications: 3 categories
      - models: 150 items
      - pathways: 3 categories
      - targets: 174 items
      [...]

2. Loading with stem_cells_regen overlay...
   ✅ Loaded 17 seed categories (core + overlay)
   📦 Overlay added: cell_types, aliases, processes, models_and_systems, markers, barriers

3. Loading with neuroscience_cognition overlay...
   ✅ Loaded 17 seed categories

4. Loading with biohacking_longevity overlay...
   ✅ Loaded 16 seed categories

5. Getting overlay metadata...
   stem_cells_v1: 6 categories, 4 exclusions
   neuroscience_v1: 6 categories, 4 exclusions
   longevity_v1: 6 categories, 4 exclusions

✅ ALL TESTS PASSED
```

---

## Integration Points

### 1. Pattern Intelligence Export (Next Step)
```python
from seed_overlay_loader import load_seeds_with_overlay
from axon_domains import get_domain_by_id

# Load domain + overlay
domain = get_domain_by_id("stem_cells_regen")
seeds = load_seeds_with_overlay("stem_cells_regen")

# Use overlay terms in extraction
# Apply domain emphasis to patterns
# Export with domain metadata
```

### 2. Scraper Enhancement (Future)
```python
# In scrape_pdfs_phase1.py or similar
seeds = load_seeds_with_overlay(args.domain)

# Extract entities using core + overlay vocabulary
# Tag entities with overlay source for transparency
```

### 3. Dashboard (Future)
- Domain switcher loads different overlays
- Display overlay-specific entity counts
- Show which terms came from overlay vs core

---

## Why This Design Works

### 1. **Prevents False Positives**
- Overlays only active when domain selected
- Stem cell terms don't pollute neuroscience analysis
- Longevity terms don't interfere with drug discovery

### 2. **Scales Safely**
- Add new overlays without touching core seeds
- Each overlay is independent
- No cross-contamination between domains

### 3. **Maintains Trust**
- Aliases anchor to full terms (prevents MS/Ki crashes)
- Exclusions filter marketing language
- Versioned (v1) for reproducibility

### 4. **Improves Pattern Detection**
- Stem cells: Better stagnation detection (engraftment, heterogeneity)
- Neuroscience: Better fragmentation detection (method diversity)
- Longevity: Better measurement trend detection (omics, clocks)

---

## Comparison: Core vs Overlay

| Aspect | Core Seeds | Overlay Seeds |
|--------|-----------|---------------|
| **When Loaded** | Always | Only when domain active |
| **Purpose** | General research vocabulary | Domain-specific terms |
| **Examples** | LC-MS, HPLC, mTOR, AMPK | iPSC, organoid, epigenetic clock |
| **Risk** | Low (well-tested) | Medium (domain-specific) |
| **Maintenance** | Stable | Can evolve per domain |

---

## Adding New Overlays

1. Copy an existing overlay JSON file
2. Update `overlay_id`, `domain`, and `notes`
3. Define entity categories relevant to new domain
4. Add aliases for abbreviations (anchor to full terms)
5. Define exclusions (marketing/hype terms)
6. Test with `python seed_overlay_loader.py`
7. Add mapping in `seed_overlay_loader.py` (line 85)

---

## Best Practices

### ✅ DO
- Anchor abbreviations to full terms via aliases
- Include translational barriers (improves stagnation detection)
- Include method diversity terms (improves fragmentation detection)
- Version overlays (v1, v2, etc.)
- Test exclusions thoroughly

### ❌ DON'T
- Add ambiguous 2-letter abbreviations directly
- Include consumer marketing terms as entities
- Mix domains (keep overlays focused)
- Overwrite core seed values
- Skip versioning

---

## Files Summary

```
seeds/
  overlays/
    stem_cells_overlay_v1.json       # Stem cell vocabulary
    neuroscience_overlay_v1.json     # Neuroscience vocabulary
    longevity_overlay_v1.json        # Longevity vocabulary

seed_overlay_loader.py               # Overlay loader + merge logic
SEED_OVERLAYS_IMPLEMENTED.md         # This file
```

---

## Status

✅ **Seed Overlay System Complete & Tested**
- 3 domain overlays created
- Python loader working
- Merge logic tested
- No pollution between domains
- Ready for integration into pattern intelligence export

**Next**: Wire overlays into pattern intelligence export (Option A from DOMAIN_SYSTEM_IMPLEMENTED.md)

---

## Key Insight

**Overlays are vocabulary, not meaning.**

They tell the engine what words to notice, not what those words mean. Meaning comes from:
- Pattern detection (convergence, escalation, etc.)
- Domain profiles (emphasis, language guardrails)
- Human interpretation (observational only)

This separation keeps the system honest and scalable.
