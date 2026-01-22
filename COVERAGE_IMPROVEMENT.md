# 📈 Entity Coverage Improvement - Phase 2

## Goal
Improve entity coverage from **28.3%** to **≥70%** by expanding seed files with domain-specific terms.

---

## Problem Analysis

After fixing the crash (false positives eliminated), entity coverage was still low at 28.3% (181/640 events).

### Root Cause
Events without entities were mostly **methodological descriptions** about:
- Sample preparation (SPE, purification, precipitation, centrifugation)
- Analytical methods (mass spectrometry, LC columns, retention time, quantitation)
- Experimental protocols (injection, incubation, validation, optimization)
- Biological processes (proteolysis, degradation, cleavage, hydrolysis)
- Proteases/enzymes (cathepsin, trypsin, MMP, calpain)

These terms were **missing from seed files**, causing low coverage.

---

## Seed File Expansions

### 1. Assays (48 → 129 terms) ✅
**Added 81 new terms:**

**Sample Preparation:**
- SPE, solid phase extraction
- purification, precipitation, centrifugation
- evaporation, lyophilization, freeze-drying
- filtration, dialysis, ultrafiltration

**Chromatography:**
- size exclusion chromatography (SEC)
- ion exchange chromatography
- affinity chromatography
- reverse phase chromatography (RP-HPLC)
- UPLC, UHPLC
- retention time, gradient elution, mobile phase

**Mass Spectrometry:**
- mass spectrometer
- MALDI-TOF, ESI-MS, QTOF, Orbitrap
- tandem mass spectrometry (MS/MS)
- selected reaction monitoring (SRM/MRM/PRM)
- data-dependent acquisition (DDA)
- data-independent acquisition (DIA)

**Analytical Validation:**
- quantitation, quantification, validation
- calibration, standard curve
- internal standard, external standard
- quality control, QC sample
- limit of detection (LOD)
- limit of quantification (LOQ)
- precision, accuracy, reproducibility

---

### 2. Targets (75 → 153 terms) ✅
**Added 78 new terms:**

**Proteases & Peptidases (CRITICAL for peptide degradation):**
- MMP1, MMP2, MMP3, MMP7, MMP9, MMP13
- matrix metalloproteinase
- ADAM10, ADAM17
- cathepsin (B, D, L)
- calpain
- trypsin, chymotrypsin, pepsin, elastase
- thrombin, plasmin, kallikrein
- dipeptidyl peptidase (DPP4/DPP-4)
- aminopeptidase, carboxypeptidase
- endopeptidase, exopeptidase
- serine protease, cysteine protease
- aspartic protease, metalloprotease
- neprilysin (NEP)
- ACE (angiotensin-converting enzyme)
- renin, furin, PCSK9
- granzyme, caspase
- proteasome subunit
- ubiquitin ligase, deubiquitinase (DUB)

**Protein Quality Control:**
- HSP70, HSP90, GRP78, BiP
- PERK, IRE1, ATF6, CHOP
- ubiquitin, SUMO

**General Enzyme Classes:**
- kinase, phosphatase
- dehydrogenase, oxidase, reductase
- transferase, hydrolase, lyase
- isomerase, ligase
- synthase, synthetase

---

### 3. Pathways (50 → 124 terms) ✅
**Added 74 new terms:**

**Protein/Peptide Processes:**
- proteolysis, protein degradation
- peptide degradation, enzymatic degradation
- hydrolysis, proteolytic cleavage, peptide cleavage
- protein synthesis, translation, transcription

**Post-Translational Modifications:**
- post-translational modification
- phosphorylation, glycosylation
- acetylation, methylation
- ubiquitination, SUMOylation
- oxidation, reduction
- disulfide bond formation

**Protein Folding & Quality:**
- protein folding, protein misfolding
- aggregation, amyloid formation, fibrillation
- ER stress, unfolded protein response (UPR)
- heat shock response

**Cellular Processes:**
- secretion, trafficking, vesicle transport
- receptor-mediated endocytosis
- phagocytosis, pinocytosis
- membrane fusion

**Signaling:**
- signal transduction, second messenger
- G protein signaling, GPCR signaling
- receptor tyrosine kinase (RTK signaling)
- cytokine signaling, chemokine signaling
- growth factor signaling, hormone signaling

**Stress & Death:**
- oxidative stress, ER stress
- immune response, inflammatory response
- cell death, necrosis, pyroptosis, ferroptosis
- senescence

**Metabolism:**
- metabolic pathway, glycolysis, gluconeogenesis
- TCA cycle, Krebs cycle
- oxidative phosphorylation
- fatty acid oxidation
- lipid metabolism, cholesterol metabolism
- amino acid metabolism

---

### 4. Models (91 → 136 terms) ✅
**Added 45 new terms:**

**Cell Culture Systems:**
- cell culture, culture medium, culture media
- growth medium, basal medium
- DMEM, RPMI, RPMI-1640, MEM, F12
- Ham's F12, Neurobasal
- conditioned medium
- serum-free medium, defined medium
- FBS (fetal bovine serum)
- bovine serum albumin (BSA)

**Experimental Systems:**
- in vitro, in vivo, in situ, ex vivo
- cell-free system
- lysate, cell lysate, tissue lysate
- extract
- microsome, mitochondria, mitochondrial
- cytoplasm, cytoplasmic
- membrane fraction, subcellular fraction

**Tissue Samples:**
- tissue, biopsy
- tumor, tumor tissue
- normal tissue, adjacent tissue
- frozen section
- paraffin-embedded, FFPE
- fresh frozen, cryopreserved

---

## Expected Impact

### Before Expansion
- **Entity Coverage**: 28.3% (181/640 events)
- **Total Seed Terms**: 253
  - Assays: 48
  - Targets: 75
  - Models: 91
  - Pathways: 50
  - Indications: 83
  - Compounds: 39

### After Expansion
- **Entity Coverage**: Target ≥70% (≥448/640 events)
- **Total Seed Terms**: 625 (+147% increase)
  - Assays: 129 (+169%)
  - Targets: 153 (+104%)
  - Models: 136 (+49%)
  - Pathways: 124 (+148%)
  - Indications: 83 (unchanged)
  - Compounds: 39 (unchanged)

---

## Key Improvements

### 1. Methodological Coverage
**Before**: Missing most analytical methods
**After**: Comprehensive coverage of:
- Sample preparation techniques
- Chromatography methods
- Mass spectrometry variants
- Analytical validation terms

### 2. Biological Process Coverage
**Before**: Only signaling pathways
**After**: Full coverage of:
- Protein degradation processes
- Post-translational modifications
- Cellular stress responses
- Metabolic pathways

### 3. Protease Coverage
**Before**: Only 5 proteases (MMP2, MMP9, ADAM10, ADAM17, BACE1)
**After**: 40+ proteases including:
- Matrix metalloproteinases (MMPs)
- Cathepsins
- Serine proteases (trypsin, chymotrypsin)
- Cysteine proteases (calpain)
- Peptidases (DPP4, aminopeptidase)

### 4. Experimental System Coverage
**Before**: Basic models only
**After**: Complete coverage of:
- Cell culture systems and media
- Experimental conditions (in vitro, in vivo, ex vivo)
- Subcellular fractions
- Tissue sample types

---

## Validation Metrics

After re-running the scraper, we expect:

✅ **Entity coverage ≥70%** (≥448/640 events)
✅ **Avg entities per event ≥1.5** (was 0.4)
✅ **Events with 2+ entities ≥40%**
✅ **Methodological events have entities** (purification, quantitation, etc.)
✅ **Biological process events have entities** (degradation, cleavage, etc.)

---

## Testing Plan

1. ✅ Expand seed files (COMPLETE)
2. ✅ Delete old database
3. ✅ Reinitialize clean database
4. ⏳ Re-run scraper with expanded seeds (IN PROGRESS)
5. ⏳ Run test_phase1_results.py
6. ⏳ Verify coverage ≥70%
7. ⏳ Check top entities are meaningful
8. ⏳ Validate no new false positives

---

## Status

- [x] Seed files expanded
- [x] Database reinitialized
- [x] Scraper running with new seeds
- [ ] Results verified
- [ ] Coverage target achieved

**Current Status**: 🔄 **SCRAPER RUNNING**

Expected completion: ~2-3 minutes

---

## Files Modified

1. ✅ `seeds/assays.json` - Added 81 analytical method terms
2. ✅ `seeds/targets.txt` - Added 78 protease/enzyme terms
3. ✅ `seeds/pathways.json` - Added 74 biological process terms
4. ✅ `seeds/models.txt` - Added 45 experimental system terms
5. ✅ `COVERAGE_IMPROVEMENT.md` - This documentation

---

**Next**: Wait for scraper to complete, then verify coverage improvement.
