# 🔧 Lab-Ready Fixes - 3 Critical Issues

## Problems Identified

### ❌ Problem 1: Targets Not Extracting (0 targets found)
**Root Cause**: 
1. Seed file loads targets as lowercase (`target.lower()`)
2. But matching checks lowercase sentence against lowercase target
3. Targets like "MTOR" become "mtor" in seed list
4. PDFs often have "mTOR" or "MTOR" - case-sensitive matching fails

**Current Code (Line 268-283)**:
```python
def extract_targets(sentence: str) -> list[dict]:
    """Extract biological targets (context-gated)"""
    targets = []
    s_l = sentence.lower()
    
    # Only extract if sentence has target context
    has_target_context = any(word in s_l for word in TARGET_CONTEXT_WORDS)
    
    if not has_target_context:
        return []
    
    # Check seed list
    for target in TARGET_SEED_LIST:  # TARGET_SEED_LIST has lowercase "mtor"
        if re.search(r'\b' + re.escape(target) + r'\b', s_l):  # Searching lowercase
            targets.append({
                "entity_type": "target",
                "entity_name": target.upper(),  # Converting back to uppercase
                "entity_variant": "protein",
                "role": "target"
            })
    
    return targets
```

**Problem**: Searching for "mtor" in lowercase sentence, but PDFs have "mTOR" which becomes "mtor" - should work, BUT context gate is too strict!

---

### ❌ Problem 2: Models Include Junk (Scaffold, Kidney, Lung, Skin)
**Root Cause**: `seeds/models.txt` includes tissue names that are too generic

**Current models.txt includes**:
```
# Tissues/Organs
liver
kidney    ← TOO GENERIC
heart
brain
lung      ← TOO GENERIC
spleen
muscle
adipose
pancreas
intestine
colon
stomach
skin      ← TOO GENERIC
bone
cartilage

# Organoids/3D Models
organoid
organoids
spheroid
spheroids
3D culture
hydrogel
scaffold  ← TOO GENERIC
```

**Problem**: These are mentioned in passing, not as experimental models.

---

### ❌ Problem 3: Named Peptides Typed Inconsistently
**Root Cause**: PLECANATIDE, ETELCALCETIDE appear in both:
- `seeds/compounds.txt` (as drugs)
- Extracted as `peptide` (from sequence patterns)

**Current Logic**:
1. Extract sequences first (finds PLECANATIDE as sequence)
2. Extract compounds second (finds plecanatide as compound)
3. Result: Same entity appears twice with different types!

---

## 🔧 Fixes

### Fix 1: Remove Context Gate for Targets (Make Extraction Work)

**Replace `extract_targets()` function** (lines 268-283):

```python
def extract_targets(sentence: str) -> list[dict]:
    """Extract biological targets - NO context gate, case-insensitive matching"""
    targets = []
    s_l = sentence.lower()
    
    # Check seed list with case-insensitive matching
    for target in TARGET_SEED_LIST:
        # Match case-insensitively
        if re.search(r'\b' + re.escape(target) + r'\b', s_l, re.IGNORECASE):
            targets.append({
                "entity_type": "target",
                "entity_name": target.upper(),
                "entity_variant": "protein",
                "role": "target"
            })
    
    return targets
```

**Changes**:
- ❌ Removed context gate (too restrictive)
- ✅ Added `re.IGNORECASE` flag for case-insensitive matching
- ✅ Now matches "MTOR", "mTOR", "mtor" all correctly

---

### Fix 2: Clean Models Seed List

**Edit `seeds/models.txt`** - Remove these lines:

```diff
# Tissues/Organs
liver
-kidney
heart
brain
-lung
spleen
muscle
adipose
pancreas
intestine
colon
stomach
-skin
bone
cartilage

# Organoids/3D Models
organoid
organoids
spheroid
spheroids
3D culture
hydrogel
-scaffold
```

**Keep only**:
- Cell lines (HEK293, HeLa, CHO, etc.)
- Organisms (mouse, rat, human, etc.)
- Biofluids (serum, plasma, blood, CSF, urine)
- Stem cells (MSC, iPSC, ESC, etc.)
- Primary cells (hepatocytes, neurons, etc.)
- Organoids (organoid, spheroid, 3D culture, hydrogel)
- Animal models (xenograft, transgenic, knockout, etc.)

**Remove**:
- Generic tissue names (kidney, lung, skin, scaffold)
- These get mentioned in passing, not as models

---

### Fix 3: Prioritize Compounds Over Peptide Sequences

**Update `extract_entities()` function** (lines 332-371):

**Current order**:
```python
# 1) PEPTIDE: Strict presentation patterns only
# 2) COMPOUND: Drug/molecule names
# 3) TARGET: Biological targets
# 4) MODEL: Experimental systems
# 5) STEM_CELL: Stem cell keywords
```

**New order** (swap 1 and 2):
```python
def extract_entities(sentence: str) -> list[dict]:
    """
    Extract all entity types with COMPOUND priority over PEPTIDE
    """
    ents = []
    s_l = sentence.lower()
    
    # Track what we've already extracted to avoid duplicates
    extracted_names = set()
    
    # 1) COMPOUND FIRST: Drug/molecule names (PRIORITY)
    for compound in COMPOUND_SEED_LIST:
        if re.search(r'\b' + re.escape(compound) + r'\b', s_l):
            name = compound.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "compound",
                    "entity_name": name,
                    "entity_variant": "drug",
                    "role": "tested"
                })
                extracted_names.add(name)
    
    # 2) PEPTIDE SEQUENCES: Only if NOT already a compound
    presented_seqs = extract_presented_sequences(sentence)
    for seq in presented_seqs:
        if is_probable_peptide(seq, sentence) and seq not in extracted_names:
            ents.append({
                "entity_type": "peptide",
                "entity_name": seq,
                "entity_variant": None,
                "role": "tested"
            })
            extracted_names.add(seq)
    
    # 3) TARGET: Biological targets
    for target in TARGET_SEED_LIST:
        if re.search(r'\b' + re.escape(target) + r'\b', s_l, re.IGNORECASE):
            name = target.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "target",
                    "entity_name": name,
                    "entity_variant": "protein",
                    "role": "target"
                })
                extracted_names.add(name)
    
    # 4) MODEL: Experimental systems
    ents.extend(extract_models(sentence))
    
    # 5) STEM_CELL: Stem cell keywords
    for k in STEM_CELL_KEYWORDS:
        if k in s_l:
            name = k.upper() if k in ["msc", "ipsc"] else k
            if name not in extracted_names:
                ents.append({
                    "entity_type": "stem_cell",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "tested"
                })
                extracted_names.add(name)
    
    return ents
```

**Changes**:
- ✅ Extract compounds FIRST (before peptides)
- ✅ Track extracted names to avoid duplicates
- ✅ PLECANATIDE, ETELCALCETIDE now always typed as "compound"
- ✅ Only unknown sequences become "peptide"

---

## 📝 Implementation Steps

### Step 1: Update scrape_pdfs.py

Replace these functions:

1. **`extract_targets()`** - Remove context gate, add case-insensitive matching
2. **`extract_entities()`** - Reorder to prioritize compounds, add deduplication

### Step 2: Clean seeds/models.txt

Remove these lines:
- kidney
- lung
- skin
- scaffold

### Step 3: Test

```bash
# Clean database
Remove-Item output/peptide_intel.sqlite

# Rebuild
python init_db.py
python scrape_pdfs.py
python export_csv.py
python check_entity_types.py
```

### Expected Results After Fixes:

```
Entities: ~25-30 total
- compound: 10 (includes PLECANATIDE, ETELCALCETIDE as drugs)
- target: 5-10 (MTOR, GLP1R, etc. now extracted!)
- model: 8-10 (clean list, no junk)
- peptide: 1-2 (only unknown sequences like KYNETWRSED)
- stem_cell: 4 (unchanged)
```

---

## ✅ Success Criteria

After implementing these fixes:

1. **Targets Extracted**: ✅ Should see 5-10 targets (MTOR, AMPK, GLP1R, etc.)
2. **Clean Models**: ✅ No more "Scaffold", "Kidney", "Lung", "Skin"
3. **Consistent Typing**: ✅ PLECANATIDE always "compound", never "peptide"

---

## 🎯 Why These Fixes Work

### Fix 1 (Targets)
- **Before**: Context gate too strict, case-sensitive matching
- **After**: No gate, case-insensitive matching
- **Result**: Targets actually get extracted!

### Fix 2 (Models)
- **Before**: Generic tissue names in seed list
- **After**: Only real experimental models
- **Result**: Clean, lab-relevant model list

### Fix 3 (Compounds vs Peptides)
- **Before**: Sequence extraction first, creates duplicates
- **After**: Compound extraction first, deduplication
- **Result**: Named peptides always typed as compounds

---

## 📊 Expected Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Targets | 0 | 5-10 | ✅ Fixed! |
| Models | 13 (4 junk) | 8-10 (clean) | ✅ Cleaner |
| Compounds | 10 | 10 | ✅ Same |
| Peptides | 3 (2 duplicates) | 1-2 (unique) | ✅ Deduplicated |
| Total Entities | 30 | 25-30 | ✅ Cleaner |

---

**Status**: Ready to implement
**Time**: 10-15 minutes
**Risk**: Low (just fixing extraction logic and seed list)
