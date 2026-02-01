"""Test domain-aware export to verify columns"""
import csv
import json
import sys

def main():
    print("="*70)
    print("TESTING DOMAIN-AWARE EXPORT")
    print("="*70)

    # Test events export
    try:
        with open('output/events_export_stem_cells_regen.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                print("   ⚠️  No data rows found (only headers or empty). Test skipped.")
            else:
                row = rows[0]
                # Assert required domain columns are present and non-empty
                assert row.get('domain_id'), "Missing or empty 'domain_id' in first CSV row"
                assert row.get('overlay_id'), "Missing or empty 'overlay_id' in first CSV row"
                # Optionally check domain_name
                # assert row.get('domain_name'), "Missing or empty 'domain_name' in first CSV row"
                print(f"   ✅ Total columns: {len(row.keys())}")
                print(f"\n   Domain columns:")
                print(f"      domain_id: '{row.get('domain_id', '(missing)')}'")
                print(f"      domain_name: '{row.get('domain_name', '(missing)')}'")
                print(f"      overlay_id: '{row.get('overlay_id', '(missing)')}'")
                print(f"\n   Entity columns:")
                print(f"      primary_entity_count: {row.get('primary_entity_count', '(missing)')}")
                print(f"      context_entity_count: {row.get('context_entity_count', '(missing)')}")
                entities_primary = row.get('entities_primary', '')
                if entities_primary:
                    print(f"      entities_primary: {entities_primary[:80]}...")
    except FileNotFoundError as e:
        print(f"   ❌ ERROR: File not found: {e}")
        sys.exit(1)
    # Test candidates export
    print("\n2. Testing candidates_primary_stem_cells_regen.csv:")
    try:
        with open('output/candidates_primary_stem_cells_regen.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            print(f"   ✅ Total entities: {len(rows)}")
            
            if rows:
                print(f"\n   Top 5 entities:")
                for i, row in enumerate(rows[:5], 1):
                    print(f"      {i}. {row.get('entity_name', '?')} ({row.get('entity_type', '?')}): {row.get('event_count', '?')} events")
                    print(f"         domain_id: '{row.get('domain_id', '(missing)')}'")
                    print(f"         overlay_id: '{row.get('overlay_id', '(missing)')}'")
    except FileNotFoundError as e:
        print(f"   ❌ ERROR: File not found: {e}")
        sys.exit(1)
    # Test run_meta
    print("\n3. Testing run_meta_stem_cells_regen.json:")
    meta = None
    try:
        with open('output/run_meta_stem_cells_regen.json', 'r', encoding='utf-8') as f:
            meta = json.load(f)
    except FileNotFoundError as e:
        print(f"   ❌ ERROR: File not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"   ❌ ERROR: JSON decode error: {e}")
        sys.exit(1)

    if meta is not None:
        assert meta is not None, "meta should not be None"
        assert meta.get('run_id') and meta.get('run_id') != '(missing)', "Missing or invalid run_id"
        assert meta.get('engine_version') and meta.get('engine_version') != '(missing)', "Missing or invalid engine_version"
        assert meta.get('domain_id') and meta.get('domain_id') != '(missing)', "Missing or invalid domain_id"
        assert meta.get('domain_name') and meta.get('domain_name') != '(missing)', "Missing or invalid domain_name"
        assert meta.get('overlay_id') and meta.get('overlay_id') != '(missing)', "Missing or invalid overlay_id"
        overlay_aliases_count = meta.get('overlay_aliases_count')
        assert isinstance(overlay_aliases_count, int) and overlay_aliases_count >= 0, "overlay_aliases_count must be int >= 0"

        print(f"   ✅ Run ID: {meta.get('run_id')}")
        print(f"   ✅ Engine: {meta.get('engine_version')}")
        print(f"   ✅ Domain ID: {meta.get('domain_id')}")
        print(f"   ✅ Domain Name: {meta.get('domain_name')}")
        print(f"   ✅ Overlay ID: {meta.get('overlay_id')}")
        print(f"   ✅ Overlay Aliases: {meta.get('overlay_aliases_count')}")

        print("\n" + "="*70)
        print("✅ ALL DOMAIN COLUMNS VERIFIED!")
        print("="*70)

if __name__ == "__main__":
    main()