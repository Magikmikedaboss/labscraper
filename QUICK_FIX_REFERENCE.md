# 🔧 Quick Fix Reference - Ambiguous Abbreviations

## Problem: False Positives from Ambiguous Abbreviations

### Symptoms
- Top entities are generic abbreviations (MS, Ki, Rb)
- Entity coverage looks high but data is wrong
- Dashboard filters show incorrect results
- Entities appear in wrong contexts

### Root Cause
Short abbreviations with multiple meanings in different domains.

---

## The 3 Critical Fixes

### 1. "MS" Ambiguity
**Problem**: "MS" = Multiple Sclerosis (medical) OR Mass Spectrometry (analytical)

**Fix**:
```json
// seeds/indications.json
{
  "indications": [
    "multiple sclerosis",  // ✅ Use full term
    // "MS",  ❌ REMOVE - too ambiguous
  ]
}
```

**Why**: In peptide research, "MS" almost always means Mass Spectrometry, not the disease.

---

### 2. "Ki" Over-extraction
**Problem**: "Ki" matches inside "kinase", "kidney", "killing"

**Fix**:
```json
// seeds/assays.json
{
  "metrics": [
    "Ki value",  // ✅ More specific
    "inhibition constant",  // ✅ Unambiguous
    // "Ki",  ❌ REMOVE - too short, causes false matches
  ]
}
```

**Why**: 2-letter abbreviations need word boundaries or longer context.

---

### 3. "Rb" Ambiguity
**Problem**: "Rb" = Retinoblastoma protein (biology) OR Rubidium (chemistry)

**Fix**:
```json
// seeds/pathways.json
{
  "pathways": [
    "Rb protein",  // ✅ More specific
    "retinoblastoma protein",  // ✅ Unambiguous
    // "Rb",  ❌ REMOVE - conflicts with chemical element
  ]
}
```

**Why**: Chemical abbreviations conflict with biological terms.

---

## Word Boundary Detection

### Problem
Substring matching causes partial word matches:
```python
if "Ki" in sentence:  # ❌ Matches "kinase", "kidney", "killing"
```

### Fix
Use regex word boundaries:
```python
if re.search(r'\b' + re.escape("Ki") + r'\b', sentence):  # ✅ Exact word only
```

### Implementation
Apply to ALL entity extraction:
- ✅ Assays
- ✅ Metrics
- ✅ Pathways
- ✅ Indications
- ✅ Compounds (already has it)
- ✅ Targets (already has it)
- ✅ Models (already has it)

---

## General Rules for Seed Files

### ✅ DO
1. **Use full terms** when possible
   - "multiple sclerosis" not "MS"
   - "inhibition constant" not "Ki"

2. **Add context** to short abbreviations
   - "Ki value" not "Ki"
   - "Rb protein" not "Rb"

3. **Use word boundaries** in extraction code
   - `\b...\b` for exact matching

4. **Test with real data** before production
   - Check top entities for false positives
   - Verify context makes sense

### ❌ DON'T
1. **Avoid 1-2 letter abbreviations** without context
   - "MS", "Ki", "Rb" are too ambiguous

2. **Don't use terms with multiple meanings**
   - Check if abbreviation has other common uses
   - Consider domain-specific conflicts

3. **Don't rely on substring matching**
   - Always use word boundaries for short terms

4. **Don't skip validation**
   - Always review top entities after changes

---

## Quick Validation Checklist

After any seed file changes:

```bash
# 1. Rebuild database
del output\peptide_intel.sqlite
python init_db.py
python scrape_pdfs_phase1.py

# 2. Check results
python test_phase1_results.py

# 3. Verify top entities
# Look for:
# ✅ Meaningful entities (LC-MS, LIRAGLUTIDE, diabetes)
# ❌ Generic abbreviations (MS, Ki, Rb)
# ❌ Partial word matches (Ki in "kinase")
```

---

## Common Ambiguous Terms to Avoid

### Medical/Analytical Conflicts
- **MS**: Multiple Sclerosis vs Mass Spectrometry
- **NMR**: Nuclear Magnetic Resonance (OK - unambiguous)
- **MRI**: Magnetic Resonance Imaging (OK - unambiguous)

### Pharmacology/Biology Conflicts
- **Ki**: Inhibition constant vs part of "kinase"
- **IC**: Inhibitory Concentration vs part of "clinical"
- **EC**: Effective Concentration (OK if word boundary used)

### Biology/Chemistry Conflicts
- **Rb**: Retinoblastoma vs Rubidium
- **Na**: Sodium (avoid - too generic)
- **K**: Potassium (avoid - too generic)
- **Ca**: Calcium (avoid - too generic)

### Safe Abbreviations (Unambiguous)
- **ELISA**: Enzyme-Linked Immunosorbent Assay ✅
- **HPLC**: High-Performance Liquid Chromatography ✅
- **qPCR**: Quantitative Polymerase Chain Reaction ✅
- **LC-MS**: Liquid Chromatography-Mass Spectrometry ✅

---

## Recovery Commands

If you encounter false positives:

```bash
# 1. Backup current database
copy output\peptide_intel.sqlite output\peptide_intel_backup.sqlite

# 2. Fix seed files (remove ambiguous terms)
# Edit seeds/*.json files

# 3. Add word boundaries to extraction code
# Edit scrape_pdfs_phase1.py

# 4. Rebuild database
del output\peptide_intel.sqlite
python init_db.py
python scrape_pdfs_phase1.py

# 5. Verify results
python test_phase1_results.py
```

---

## Success Criteria

After fixes, you should see:

✅ **Top 10 entities are meaningful**
- LC-MS, mass spectrometry, LIRAGLUTIDE, GLUCAGON, etc.

✅ **No false positives in top entities**
- No "MS" as disease when it means Mass Spec
- No "Ki" from partial "kinase" matches

✅ **Entity coverage ≥70%**
- Most events have at least one entity

✅ **Confidence distribution improved**
- Not 94% low confidence

---

## Reference

- **Diagnosis**: `CRASH_DIAGNOSIS.md`
- **Recovery Plan**: `RECOVERY_PLAN.md`
- **Full Summary**: `CRASH_RECOVERY_SUMMARY.md`
- **This Guide**: `QUICK_FIX_REFERENCE.md`

---

**Last Updated**: During crash recovery
**Status**: Fixes implemented, database rebuilding
