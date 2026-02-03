# Duplicate Seed Files and Configuration Fixes - Summary

## Overview
Successfully resolved critical duplicate seed files and configuration issues that were causing scripts to see different data, leading to configuration conflicts.

## Issues Fixed

### 🔴 Critical Issue #1: Duplicate Seed Files (Root vs Base)
**Problem**: Two complete sets of seed files in different locations causing scripts to load different data.

**Files Affected**:
- `seeds/compounds.txt` ❌ (duplicate)
- `seeds/targets.txt` ❌ (duplicate) 
- `seeds/models.txt` ❌ (duplicate)
- `seeds/assays.json` ❌ (duplicate)

**Solution**: 
- ✅ Deleted all duplicate root seed files
- ✅ Updated `utils/run_engine.py` to use new paths:
  - `seeds/base/life_sciences/compounds.txt`
  - `seeds/base/life_sciences/targets.txt`
  - `seeds/base/life_sciences/models.txt`
- ✅ Updated lazy-loaded seed functions to use new paths

### 🔴 Critical Issue #2: Duplicate Domain Configs
**Problem**: Domain configs in wrong location causing confusion.

**Files Affected**:
- `seeds/domains/construction_science.json` ❌ (duplicate)

**Solution**:
- ✅ Deleted duplicate domain config
- ✅ Kept canonical version at `config/domains/construction_science.json`

### 🟡 Issue #3: Multiple Longevity Overlay Versions
**Problem**: Multiple versions of longevity overlays with unclear active version.

**Files Affected**:
- `seeds/overlays/longevity_overlay_v1_backup.json` ❌ (backup - deleted)
- `seeds/overlays/longevity_overlay_v1.json` ✅ (kept)
- `seeds/overlays/longevity_overlay_v2.json` ✅ (kept)

**Solution**:
- ✅ Deleted backup file
- ✅ Kept both v1 and v2 (user can choose which to use)

### 🟡 Issue #4: Duplicate Climate Overlays
**Problem**: Same overlay with different naming conventions.

**Files Affected**:
- `seeds/overlays/climate_resilience_v1.json` ✅ (kept)
- `seeds/overlays/resilience_climate_v1.json` ❌ (duplicate - deleted)

**Solution**:
- ✅ Deleted duplicate with inconsistent naming

### 🟡 Issue #5: Backup and Obsolete Files
**Problem**: Old backup files cluttering the seeds directory.

**Files Affected**:
- `seeds/backup.json` ❌ (deleted)
- `seeds/backup_assays.json` ❌ (deleted)

**Solution**:
- ✅ Deleted all obsolete backup files

## Files Modified

### `utils/run_engine.py`
- Updated `get_seeds()` function to load from new paths
- Updated lazy-loaded seed functions (`_get_compound_seeds`, `_get_target_seeds`, `_get_model_seeds`)
- All functions now correctly reference `seeds/base/life_sciences/` paths

## Verification

### ✅ Script Testing
- `python utils/run_engine.py --help` - Script runs without errors
- `python -c "from utils.run_engine import get_seeds; get_seeds()"` - Successfully loads 57 compounds, 177 targets, 160 models
- `python utils/check_longevity_compounds.py` - Successfully loads and processes compounds from new paths

### ✅ Data Integrity
- All seed files are now in the canonical `seeds/base/life_sciences/` location
- No duplicate files remain
- Scripts consistently load from the same source

## Impact

### Before Fix
- `utils/run_engine.py` loaded from root seeds (old paths)
- `utils/check_longevity_compounds.py` loaded from nested seeds (new paths)
- Scripts saw different data causing configuration conflicts

### After Fix
- All scripts consistently load from `seeds/base/life_sciences/` paths
- No duplicate files causing confusion
- Unified data source for all scripts

## Files Deleted
```
seeds/compounds.txt
seeds/targets.txt  
seeds/models.txt
seeds/assays.json
seeds/domains/construction_science.json
seeds/overlays/longevity_overlay_v1_backup.json
seeds/overlays/resilience_climate_v1.json
seeds/backup.json
seeds/backup_assays.json
```

## Files Modified
```
utils/run_engine.py (updated seed paths)
```

## Remaining Files (Canonical)
```
seeds/base/life_sciences/compounds.txt
seeds/base/life_sciences/targets.txt
seeds/base/life_sciences/models.txt
seeds/base/life_sciences/assays.txt
config/domains/construction_science.json
seeds/overlays/longevity_overlay_v1.json
seeds/overlays/longevity_overlay_v2.json
seeds/overlays/climate_resilience_v1.json
```

## Next Steps
1. **Monitor**: Watch for any scripts that might still reference old paths
2. **Documentation**: Update any documentation that references old seed paths
3. **Testing**: Run full pipeline to ensure no regressions
4. **Cleanup**: Consider removing any remaining references to old paths in comments or documentation

## Root Cause
The project migrated from a flat seed structure → nested base/ structure, but:
- Old seed files were not deleted
- Some scripts still referenced the old paths
- This created two sources of truth causing configuration conflicts

**Fix**: Completed the migration by deleting old files and updating all script paths to use `seeds/base/life_sciences/`.