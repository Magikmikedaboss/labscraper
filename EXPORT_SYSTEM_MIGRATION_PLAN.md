# Export System Migration Plan

## Overview

This document outlines the migration plan to consolidate the duplicate export functions in the peptide-scraper project. Currently there are multiple export systems with overlapping functionality that need to be unified.

## Current State Analysis

### Duplicate Export Functions Identified

1. **Root Level (1 file)**
   - `export_csv_v4_professional.py` - Main export script

2. **Utils Directory (3 files)**
   - `utils/export_csv_v4_professional.py` - Duplicate of root level
   - `utils/export_csv_v5_domain_aware.py` - Domain-aware version
   - `utils/export_csv_v5_domain_aware_fixed.py` - "Fixed" version of v5

3. **Test Files (2 files)**
   - `utils/test_v4_exports.py` - Tests for v4 exports
   - `utils/test_v4_exports_fixed.py` - "Fixed" version of v4 tests

## Migration Strategy

### Phase 1: Immediate Cleanup (Priority: HIGH)

**Action Items:**
1. Remove `export_csv_v4_professional.py` from root directory
2. Remove `utils/export_csv_v4_professional.py` (duplicate)
3. Remove `utils/test_v4_exports_fixed.py` (duplicate test file)

**Rationale:**
- Eliminates confusion about which export system to use
- Reduces maintenance overhead
- Removes redundant test coverage

### Phase 2: System Consolidation (Priority: HIGH)

**Decision: Keep v5 Domain-Aware System**

**Rationale:**
- v5 has all v4 features plus domain awareness
- Supports overlay aliases for normalization
- More extensible for future domains
- Better architecture with command-line arguments

**Migration Steps:**
1. Rename `utils/export_csv_v5_domain_aware.py` to `utils/export_csv.py`
2. Update all imports and references to use the new consolidated name
3. Ensure v5 has all v4 functionality (confidence boost, process word demotion, etc.)

### Phase 3: Documentation and Testing (Priority: MEDIUM)

**Action Items:**
1. Update README with clear export system documentation
2. Create migration guide for users
3. Add comprehensive tests for the consolidated system
4. Document the differences between v4 and v5 features

## Implementation Plan

### Step 1: Remove Duplicates

```bash
# Remove duplicate files
rm export_csv_v4_professional.py
rm utils/export_csv_v4_professional.py
rm utils/test_v4_exports_fixed.py
```

### Step 2: Consolidate v5 System

```bash
# Rename v5 to be the primary export system
mv utils/export_csv_v5_domain_aware.py utils/export_csv.py
```

### Step 3: Update References

Update all files that reference the old export functions:

- `test_v4_exports.py` → `test_export_system.py`
- Any import statements in other modules
- Documentation files
- README references

### Step 4: Verify Functionality

1. Run comprehensive tests to ensure no functionality is lost
2. Test both domain-specific and general exports
3. Verify all v4 features work in the consolidated system

## File Mapping

| Old File | New File | Status |
|----------|----------|---------|
| `export_csv_v4_professional.py` | **REMOVE** | ✅ |
| `utils/export_csv_v4_professional.py` | **REMOVE** | ✅ |
| `utils/export_csv_v5_domain_aware.py` | `utils/export_csv.py` | ✅ |
| `utils/export_csv_v5_domain_aware_fixed.py` | Keep (has fixes) | ⚠️ |
| `utils/test_v4_exports.py` | `utils/test_export_system.py` | ✅ |
| `utils/test_v4_exports_fixed.py` | **REMOVE** | ✅ |

## Risk Assessment

### Low Risk
- Removing duplicate files (no functionality loss)
- Renaming files (straightforward operation)

### Medium Risk
- Ensuring v5 has all v4 functionality
- Updating all references correctly

### Mitigation Strategies
- Comprehensive testing before and after changes
- Backup all files before removal
- Test with sample data to verify functionality

## Timeline

### Day 1: Cleanup Phase ✅ COMPLETED
- [x] Remove duplicate files
- [x] Verify no broken imports

### Day 2: Consolidation Phase ✅ COMPLETED
- [x] Rename v5 to primary export system
- [x] Update all references
- [x] Run basic functionality tests

### Day 3: Testing and Documentation ✅ COMPLETED
- [x] Comprehensive testing
- [x] Update documentation
- [x] Create migration guide

## Success Criteria

1. **No duplicate export functions** - Only one export system remains
2. **All functionality preserved** - v4 features work in consolidated system
3. **Clear documentation** - Users know which system to use
4. **No broken references** - All imports and calls work correctly
5. **Comprehensive tests** - Full test coverage of consolidated system

## Post-Migration Maintenance

### Ongoing Tasks
1. Monitor for any issues with the consolidated system
2. Update documentation as needed
3. Consider deprecating v4-specific features if v5 is fully compatible

### Future Improvements
1. Add more domain-specific export features
2. Improve error handling and user feedback
3. Consider adding export format options (JSON, Excel, etc.)

## Notes

- The `utils/export_csv_v5_domain_aware_fixed.py` file contains important fixes and should be reviewed before removal
- Ensure all configuration files and scripts that call these exports are updated
- Consider adding version checking to prevent confusion about which system is active