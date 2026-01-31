"""
Cleanup Obsolete Files
Removes old export scripts and documentation that have been superseded by v5
"""


import argparse
from pathlib import Path
import os

# Use BASE_DIR for safe file operations
BASE_DIR = Path(__file__).resolve().parent

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

def remove_files(file_list, label, dry_run=False):
    """Helper to remove files from a list"""
    removed_count = 0
    print(f"\n{label}:")
    for filepath in file_list:
        try:
            path = (BASE_DIR / filepath).resolve()
            # Ensure path is inside BASE_DIR
            # Ensure path is inside BASE_DIR using Path containment
            try:
                # Python 3.9+: use is_relative_to
                if hasattr(path, 'is_relative_to'):
                    if not path.is_relative_to(BASE_DIR):
                        print(f"   ❌ Skipped (outside_BASE_DIR): {filepath}")
                        continue
                else:
                    # Fallback for Python <3.9
                    path.relative_to(BASE_DIR)
            except ValueError:
                print(f"   ❌ Skipped (outside_BASE_DIR): {filepath}")
                continue
            if path.exists():
                if dry_run:
                    print(f"   🔍 Would remove: {filepath}")
                    removed_count += 1
                else:
                    try:
                        path.unlink()
                        print(f"   ✅ Removed: {filepath}")
                        removed_count += 1
                    except OSError as e:
                        print(f"   ❌ Failed to remove {filepath}: {e}")
            else:
                print(f"   ⏭️  Already gone: {filepath}")
        except Exception as e:
            print(f"   ❌ Error resolving {filepath}: {e}")
    return removed_count

def cleanup(dry_run=False):
    """Remove obsolete files"""
    print("=" * 70)
    if dry_run:
        print("DRY RUN - CLEANING UP OBSOLETE FILES")
    else:
        print("CLEANING UP OBSOLETE FILES")
    print("=" * 70)
    
    removed_count = 0
    
    # Remove obsolete files
    removed_count += remove_files(OBSOLETE_FILES, "📁 Removing obsolete files", dry_run)
    
    # Remove obsolete outputs
    removed_count += remove_files(OBSOLETE_OUTPUTS, "📊 Removing obsolete exports", dry_run)
    
    print("\n" + "=" * 70)
    if dry_run:
        print(f"🔍 Dry run complete! Would remove {removed_count} files")
    else:
        print(f"✅ Cleanup complete! Removed {removed_count} files")
    print("=" * 70)
    
    print("\n📋 Keeping:")
    print("   ✅ export_csv_v4_professional.py (stable v4)")
    print("   ✅ export_csv_v5_domain_aware.py (latest with domain support)")
    print("   ✅ All current exports in output/")
    print("   ✅ All domain and overlay files")
    print("   ✅ Core documentation (DOMAIN_EXPORT_V5_SUMMARY.md, etc.)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup obsolete files")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be removed without actually deleting')
    args = parser.parse_args()
    
    cleanup(dry_run=args.dry_run)
