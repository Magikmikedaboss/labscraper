"""
Clean up old export files, keep only v4 production files
"""
from pathlib import Path

OUTPUT_DIR = Path("output")

# Files to DELETE (old versions)
old_files = [
    "candidates_context.csv",      # Old v3
    "candidates_export_v3.csv",    # Old v3
    "candidates_primary.csv",      # Old v3
    "events_export_v3.csv",        # Old v3
]

# Files to KEEP (v4 production)
keep_files = [
    "events_export_v4.csv",        # ✅ USE THIS
    "candidates_primary_v4.csv",   # ✅ USE THIS
    "run_meta.json",               # ✅ USE THIS
    "peptide_intel.sqlite",        # ✅ Source database
    "README.md",                   # ✅ Documentation
]

print("="*70)
print("🧹 CLEANING UP OLD EXPORTS")
print("="*70)

deleted = []
for old_file in old_files:
    file_path = OUTPUT_DIR / old_file
    if file_path.exists():
        file_path.unlink()
        deleted.append(old_file)
        print(f"🗑️  Deleted: {old_file}")
    else:
        print(f"⏭️  Already gone: {old_file}")

print(f"\n✅ Deleted {len(deleted)} old files")

print("\n" + "="*70)
print("📁 PRODUCTION FILES (KEEP THESE)")
print("="*70)

for keep_file in keep_files:
    file_path = OUTPUT_DIR / keep_file
    if file_path.exists():
        size = file_path.stat().st_size
        print(f"✅ {keep_file} ({size:,} bytes)")
    else:
        print(f"❌ MISSING: {keep_file}")

print("\n" + "="*70)
print("📋 WHICH FILES TO USE")
print("="*70)
print("\n🎯 For Next.js Integration:")
print("   1. events_export_v4.csv       - All 647 events with v4 features")
print("   2. candidates_primary_v4.csv  - 107 primary entities (clean rankings)")
print("   3. run_meta.json              - Run metadata (optional)")
print("\n💾 Keep for Reference:")
print("   - peptide_intel.sqlite        - Source database")
print("   - README.md                   - Documentation")

print("\n✅ Cleanup complete!")
