import os
import sys
import time
from pathlib import Path

OUTPUT_DIR = Path("output")

def main() -> int:
    print("=" * 70)
    print("ALL CSV EXPORTS WITH TIMESTAMPS")
    print("=" * 70)

    csv_files = [
        "candidates_primary_v4.csv",
        "events_export_v4.csv",
        "pattern_intelligence_export.csv",
    ]

    print("\n📊 CSV Files in output/:\n")

    missing_files = []
    existing_files = []

    for index, filename in enumerate(csv_files, 1):
        filepath = OUTPUT_DIR / filename
        if filepath.exists():
            mod_time = os.path.getmtime(filepath)
            mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
            size_bytes = os.path.getsize(filepath)
            size_kb = size_bytes / 1024

            print(f"{index}. {filename}")
            print(f"   📅 Modified: {mod_time_str}")
            print(f"   📦 Size: {size_kb:.1f} KB")
            print()

            existing_files.append(filename)
        else:
            missing_files.append(filename)
            print(f"{index}. {filename}")
            print("   ❌ NOT FOUND")
            print()

    print("=" * 70)

    if not missing_files:
        print(f"\n✅ All {len(csv_files)} CSV exports are current!")
        print("\nTo open them:")
        for filename in existing_files:
            if sys.platform.startswith("win"):
                print(f"  start output/{filename}")
            elif sys.platform.startswith("darwin"):
                print(f"  open output/{filename}")
            else:
                print(f"  xdg-open output/{filename}")
    else:
        print(f"\n⚠️  Missing {len(missing_files)} file(s):")
        for filename in missing_files:
            print(f"   - {filename}")

    if missing_files and existing_files:
        print(f"\n✅ Found {len(existing_files)} file(s):")
        print("\nTo open existing files:")
        for filename in existing_files:
            if sys.platform.startswith("win"):
                print(f"  start output/{filename}")
            elif sys.platform.startswith("darwin"):
                print(f"  open output/{filename}")
            else:
                print(f"  xdg-open output/{filename}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
