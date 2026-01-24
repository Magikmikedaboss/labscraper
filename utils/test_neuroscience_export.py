import csv
import json
from pathlib import Path

def test_neuroscience_export():
    """Test the neuroscience cognition export files"""
    
    print("\n" + "="*70)
    print("TESTING NEUROSCIENCE COGNITION EXPORT")
    print("="*70)
    
    # Load metadata
    meta_file = Path("output/run_meta_neuroscience_cognition.json")
    with open(meta_file, 'r') as f:
        meta = json.load(f)
    
    print(f"\n📊 METADATA:")
    print(f"  Run ID: {meta['run_id']}")
    print(f"  Engine: {meta['engine_version']}")
    print(f"  Domain: {meta['domain_name']}")
    print(f"  Total Events: {meta['counts']['total_events']}")
    print(f"  Total Entities: {meta['counts']['total_entities']}")
    print(f"  Primary Entities: {meta['counts']['primary_entities']}")
    print(f"  Context Entities: {meta['counts']['context_entities']}")
    
    # Test events CSV
    events_file = Path("output/events_export_neuroscience_cognition.csv")
    with open(events_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        events = list(reader)
    
    print(f"\n✅ EVENTS CSV:")
    print(f"  File: {events_file.name}")
    print(f"  Rows: {len(events)} (expected: {meta['counts']['total_events']})")
    print(f"  Match: {'✅ YES' if len(events) == meta['counts']['total_events'] else '❌ NO'}")
    if events:
        print(f"  Columns: {len(events[0].keys())}")
    else:
        print(f"  Columns: 0 (N/A)")
    
    # Test candidates CSV
    candidates_file = Path("output/candidates_primary_neuroscience_cognition.csv")
    with open(candidates_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)
    
    print(f"\n✅ CANDIDATES CSV:")
    print(f"  File: {candidates_file.name}")
    print(f"  Rows: {len(candidates)} (expected: {meta['counts']['primary_entities']})")
    print(f"  Match: {'✅ YES' if len(candidates) == meta['counts']['primary_entities'] else '❌ NO'}")
    
    # Show top entities
    print(f"\n📈 TOP 10 ENTITIES:")
    for i, cand in enumerate(candidates[:10], 1):
        print(f"  {i:2d}. {cand['entity_name']:25s} ({cand['entity_type']:12s}) - {cand['event_count']:>4s} events")
    
    # Confidence distribution
    print(f"\n📊 CONFIDENCE DISTRIBUTION:")
    conf_dist = meta['confidence_distribution']
    print(f"  High: {conf_dist['high']}")
    print(f"  Med:  {conf_dist['med']}")
    print(f"  Low:  {conf_dist['low']}")
    print(f"  Boosted to High: {conf_dist['boosted_to_high']}")
    
    # Sample events by type
    event_types = {}
    for event in events[:100]:  # Sample first 100
        et = event['event_type']
        event_types[et] = event_types.get(et, 0) + 1
    
    print(f"\n📋 EVENT TYPES (sample of first 100):")
    for et, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {et:30s}: {count}")
    
    # Entity type distribution
    entity_types = {}
    for cand in candidates:
        et = cand['entity_type']
        entity_types[et] = entity_types.get(et, 0) + 1
    
    print(f"\n🏷️  ENTITY TYPE DISTRIBUTION:")
    for et, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {et:20s}: {count:>4d}")
    
    # Final verdict
    print("\n" + "="*70)
    print("EXPORT VALIDATION SUMMARY")
    print("="*70)
    
    all_good = True
    
    if len(events) == meta['counts']['total_events']:
        print("✅ Events count matches metadata")
    else:
        print(f"❌ Events count mismatch: {len(events)} vs {meta['counts']['total_events']}")
        all_good = False
    
    if len(candidates) == meta['counts']['primary_entities']:
        print("✅ Candidates count matches metadata")
    else:
        print(f"❌ Candidates count mismatch: {len(candidates)} vs {meta['counts']['primary_entities']}")
        all_good = False
    
    if events_file.exists() and candidates_file.exists():
        print("✅ Both export files exist")
    else:
        print("❌ Missing export files")
        all_good = False
    
    if len(events) > 0 and len(candidates) > 0:
        print("✅ Both files contain data")
    else:
        print("❌ Empty export files")
        all_good = False
    
    print("\n" + "="*70)
    if all_good:
        print("🎉 EXPORT SUCCESSFUL - All validations passed!")
    else:
        print("⚠️  EXPORT COMPLETED WITH WARNINGS")
    print("="*70)

if __name__ == "__main__":
    test_neuroscience_export()
