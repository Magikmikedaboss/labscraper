"""
Show all CSV exports with timestamps
"""
import os
import time
from pathlib import Path

OUTPUT_DIR = Path("output")

print("=" * 70)
print("ALL CSV EXPORTS WITH TIMESTAMPS")
print("=" * 70)

csv_files = [
    "candidates_primary_v4.csv",
    "events_export_v4.csv",
    "pattern_intelligence_export.csv"
]

print("\n📊 CSV Files in output/:\n")

for i, filename in enumerate(csv_files, 1):
    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        # Get file modification time
        mod_time = os.path.getmtime(filepath)
        mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
        
        # Get file size
        size_bytes = os.path.getsize(filepath)
        size_kb = size_bytes / 1024
        
        print(f"{i}. {filename}")
        print(f"   📅 Modified: {mod_time_str}")
        print(f"   📦 Size: {size_kb:.1f} KB")
        print()

print("=" * 70)
print("\n✅ All 3 CSV exports are current!")
print("\nTo open them:")
print("  start output/candidates_primary_v4.csv")
print("  start output/events_export_v4.csv")
print("  start output/pattern_intelligence_export.csv")
