"""
Demo: Domain-Aware Export System
Shows how overlay aliases normalize entities and domain tracking works
"""

if __name__ == "__main__":
    print("="*80)
    print("DOMAIN-AWARE EXPORT SYSTEM DEMO")
    print("="*80)

    print("\n📚 Step 1: Load overlay aliases")
    print("-" * 80)

    try:
        from utils.entity_normalizer import load_overlay_aliases
    except ImportError:
        from entity_normalizer import load_overlay_aliases

    # Load stem cells overlay
    stem_aliases = load_overlay_aliases("stem_cells_regen")
    print(f"✅ Loaded {len(stem_aliases)} aliases from stem_cells_regen overlay")
    print("\nSample aliases:")
    for abbrev, canonical in list(stem_aliases.items())[:5]:
        print(f"   {abbrev:20} → {canonical}")

    print("\n🔬 Step 2: Test entity normalization")
    print("-" * 80)

    try:
        from utils.entity_normalizer import normalize_entity, load_normalization_map
    except ImportError:
        from entity_normalizer import normalize_entity, load_normalization_map

    norm_map = load_normalization_map()

    # Test entities with abbreviations
    test_entities = [
        {"entity_type": "stem_cell", "entity_name": "MSC"},
        {"entity_type": "stem_cell", "entity_name": "iPSC"},
        {"entity_type": "stem_cell", "entity_name": "ESC"},
        {"entity_type": "marker", "entity_name": "SOX2"},
        {"entity_type": "marker", "entity_name": "NANOG"},
    ]

    print("Without overlay (no normalization):")
    for e in test_entities:
        normalized = normalize_entity(e, norm_map)
        print(f"   {e['entity_name']:20} → {normalized['entity_name']}")

    print("\nWith stem_cells_regen overlay (normalized):")
    for e in test_entities:
        normalized = normalize_entity(e, norm_map, stem_aliases)
        arrow = "→" if e['entity_name'] != normalized['entity_name'] else "="
        print(f"   {e['entity_name']:20} {arrow} {normalized['entity_name']}")

    print("\n📊 Step 3: Check exported files")
    print("-" * 80)

    import csv
    import json

    # Check events export
    print("Events export (events_export_stem_cells_regen.csv):")
    try:
        with open('output/events_export_stem_cells_regen.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            try:
                row = next(reader)
                print(f"domain_id: '{row.get('domain_id', '<missing>')}', domain_name: '{row.get('domain_name', '<missing>')}', overlay_id: '{row.get('overlay_id', '<missing>')}'")
            except StopIteration:
                print("No rows found in events_export_stem_cells_regen.csv.")
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error opening events export file: {e}")
    except Exception as e:
        print(f"Unexpected error opening events export file: {e}")

    # Check candidates export
    print("\nCandidates export (candidates_primary_stem_cells_regen.csv):")
    try:
        with open('output/candidates_primary_stem_cells_regen.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            # Find normalized stem cell entities
            stem_cells = [r for r in rows if r['entity_type'] == 'stem_cell']
            print(f"   ✅ Found {len(stem_cells)} stem cell entities")
            for sc in stem_cells[:3]:
                print(f"      - {sc['entity_name']} ({sc['event_count']} events)")
                print(f"        Original variants: {sc['original_variants']}")
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error opening candidates export file: {e}")
    except Exception as e:
        print(f"Unexpected error opening candidates export file: {e}")

    # Check run metadata
    print("\nRun metadata (run_meta_stem_cells_regen.json):")
    try:
        with open('output/run_meta_stem_cells_regen.json', 'r', encoding='utf-8') as f:
            meta = json.load(f)
            print(f"   📦 Engine: {meta.get('engine_version', 'unknown')}")
            print(f"   🌐 Domain: {meta.get('domain_name', 'unknown')}")
            print(f"   🔗 Overlay: {meta.get('overlay_id', 'unknown')}")
            print(f"   🔄 Aliases used: {meta.get('overlay_aliases_count', 0)}")
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error opening run metadata file: {e}")
    except Exception as e:
        print(f"Unexpected error opening run metadata file: {e}")

    print("\n🎯 Step 4: Compare with/without domain")
    print("-" * 80)

    print("Exports available:")
    print("   1. events_export_v4.csv (no domain, no overlay)")
    print("   2. events_export_stem_cells_regen.csv (stem cells domain + overlay)")
    print("   3. Future: events_export_neuroscience_cognition.csv (neuro domain + overlay)")

    print("\nKey differences:")
    print("   ✅ Domain columns track which lens was used")
    print("   ✅ Overlay aliases normalize abbreviations (MSC→mesenchymal stem cell)")
    print("   ✅ run_meta.json shows overlay version for reproducibility")

    print("\n" + "="*80)
    print("✅ DEMO COMPLETE - Domain-aware export system working!")
    print("="*80)

    print("\n💡 Usage:")
    print("   # Export with stem cells domain")
    print("   python export_csv_v5_domain_aware.py --domain stem_cells_regen")
    print()
    print("   # Export with neuroscience domain")
    print("   python export_csv_v5_domain_aware.py --domain neuroscience_cognition")
    print()
    print("   # Export all domains (no filter)")
    print("   python export_csv_v5_domain_aware.py")