"""Test domain-aware export to verify columns"""
import csv

print("="*70)
print("TESTING DOMAIN-AWARE EXPORT")
print("="*70)

# Test events export
print("\n1. Testing events_export_stem_cells_regen.csv:")
with open('output/events_export_stem_cells_regen.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    row = next(reader)
    
    print(f"   ✅ Total columns: {len(row.keys())}")
    print(f"\n   Domain columns:")
    print(f"      domain_id: '{row['domain_id']}'")
    print(f"      domain_name: '{row['domain_name']}'")
    print(f"      overlay_id: '{row['overlay_id']}'")
    
    print(f"\n   Entity columns:")
    print(f"      primary_entity_count: {row['primary_entity_count']}")
    print(f"      context_entity_count: {row['context_entity_count']}")
    
    if row['entities_primary']:
        print(f"      entities_primary: {row['entities_primary'][:80]}...")

# Test candidates export
print("\n2. Testing candidates_primary_stem_cells_regen.csv:")
with open('output/candidates_primary_stem_cells_regen.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
    print(f"   ✅ Total entities: {len(rows)}")
    
    # Show first few entities
    print(f"\n   Top 5 entities:")
    for i, row in enumerate(rows[:5], 1):
        print(f"      {i}. {row['entity_name']} ({row['entity_type']}): {row['event_count']} events")
        print(f"         domain_id: '{row['domain_id']}'")
        print(f"         overlay_id: '{row['overlay_id']}'")

# Test run_meta
print("\n3. Testing run_meta_stem_cells_regen.json:")
import json
with open('output/run_meta_stem_cells_regen.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)
    
    print(f"   ✅ Run ID: {meta['run_id']}")
    print(f"   ✅ Engine: {meta['engine_version']}")
    print(f"   ✅ Domain ID: {meta['domain_id']}")
    print(f"   ✅ Domain Name: {meta['domain_name']}")
    print(f"   ✅ Overlay ID: {meta['overlay_id']}")
    print(f"   ✅ Overlay Aliases: {meta['overlay_aliases_count']}")

print("\n" + "="*70)
print("✅ ALL DOMAIN COLUMNS VERIFIED!")
print("="*70)
