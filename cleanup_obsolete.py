"""
Cleanup Obsolete Files
Removes old export scripts and documentation that have been superseded by v5
"""

import os
from pathlib import Path

# Files to remove
OBSOLETE_FILES = [
    # Old export scripts (superseded by v5)
    "export_csv.py",
    "export_csv_v2.py",
    "export_csv_v3.py",
    
    # Old test scripts (superseded by test_domain_export.py)
    "check_results.py",
    
    # Obsolete documentation (consolidated into newer docs)
    "PRODUCTION_BLOCKERS.md",
    "RECOVERY_PLAN.md",
    "QUICK_FIX_REFERENCE.md",
    "THREE_FIXES_SUMMARY.md",
    "UPGRADE_SUMMARY.md",
    "CONTEXT_GATE_SOLUTION.md",
    "TESTING_STATUS.md",
    
    # Duplicate bug fix docs (consolidated into BUG_FIXES_FINAL.md)
    "BUG_FIXES_BATCH.md",
    
    # Old utility scripts
    "cleanup_old_exports.py",
]

# Output files to remove (old exports)
OBSOLETE_OUTPUTS = [
    "output/candidates_export.csv",
    "output/events_export.csv",
    "output/measurements_export.csv",
    "output/relationships_export.csv",
]

def cleanup():
    """Remove obsolete files"""
    print("=" * 70)
    print("CLEANING UP OBSOLETE FILES")
    print("=" * 70)
    
    removed_count = 0
    
    # Remove obsolete files
    print("\n📁 Removing obsolete files:")
    for filepath in OBSOLETE_FILES:
        path = Path(filepath)
        if path.exists():
            try:
                path.unlink()
                print(f"   ✅ Removed: {filepath}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {filepath}: {e}")
        else:
            print(f"   ⏭️  Already gone: {filepath}")
    
    # Remove obsolete outputs
    print("\n📊 Removing obsolete exports:")
    for filepath in OBSOLETE_OUTPUTS:
        path = Path(filepath)
        if path.exists():
            try:
                path.unlink()
                print(f"   ✅ Removed: {filepath}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {filepath}: {e}")
        else:
            print(f"   ⏭️  Already gone: {filepath}")
    
    print("\n" + "=" * 70)
    print(f"✅ Cleanup complete! Removed {removed_count} files")
    print("=" * 70)
    
    print("\n📋 Keeping:")
    print("   ✅ export_csv_v4_professional.py (stable v4)")
    print("   ✅ export_csv_v5_domain_aware.py (latest with domain support)")
    print("   ✅ All current exports in output/")
    print("   ✅ All domain and overlay files")
    print("   ✅ Core documentation (DOMAIN_EXPORT_V5_SUMMARY.md, etc.)")

if __name__ == "__main__":
    cleanup()
