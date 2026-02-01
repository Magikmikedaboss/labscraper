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
    if not meta_file.exists():
        print(f"❌ ERROR: Metadata file not found: {meta_file}")
        return
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in metadata file: {e}")
        return
    
    print(f"\n📊 METADATA:")
    print(f"  Run ID: {meta.get('run_id', 'N/A')}")
    print(f"  Engine: {meta.get('engine_version', 'N/A')}")
    print(f"  Domain: {meta.get('domain_name', 'N/A')}")
    counts = meta.get('counts', {})
    print(f"  Total Events: {counts.get('total_events', 'N/A')}")
    print(f"  Total Entities: {counts.get('total_entities', 'N/A')}")
    print(f"  Primary Entities: {counts.get('primary_entities', 'N/A')}")
    print(f"  Context Entities: {counts.get('context_entities', 'N/A')}")
    
    # Test events and candidates CSV existence early
    events_file = Path("output/events_export_neuroscience_cognition.csv")
    candidates_file = Path("output/candidates_primary_neuroscience_cognition.csv")
    if not events_file.exists() or not candidates_file.exists():
        print(f"❌ ERROR: Missing export file(s):")
        if not events_file.exists():
            print(f"   - {events_file}")
        if not candidates_file.exists():
            print(f"   - {candidates_file}")
        print("❌ Missing export files. Aborting test.")
        return

    with open(events_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        events = list(reader)

    expected_events = meta.get('counts', {}).get('total_events', 'N/A')
    print(f"  Rows: {len(events)} (expected: {expected_events})")
    print(f"  Match: {'✅ YES' if expected_events != 'N/A' and len(events) == expected_events else '❌ NO'}")
    if events:
        print(f"  Columns: {len(events[0].keys())}")
    else:
        print(f"  Columns: 0 (N/A)")

    with open(candidates_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    print(f"\n✅ CANDIDATES CSV:")
    print(f"  File: {candidates_file.name}")
    expected_primary = meta.get('counts', {}).get('primary_entities', 'N/A')
    print(f"  Rows: {len(candidates)} (expected: {expected_primary})")
    print(f"  Match: {'✅ YES' if expected_primary != 'N/A' and len(candidates) == expected_primary else '❌ NO'}")    
    # Show top entities
    print(f"\n📈 TOP 10 ENTITIES:")
    for i, cand in enumerate(candidates[:10], 1):
        name = str(cand.get('entity_name', '<missing>'))
        etype = str(cand.get('entity_type', '<missing>'))
        count = str(cand.get('event_count', '0'))
        try:
            print(f"  {i:2d}. {name:25s} ({etype:12s}) - {count:>4s} events")
        except Exception:
            print(f"  {i:2d}. <malformed row>: {cand}")
    
    # Confidence distribution
    print(f"\n📊 CONFIDENCE DISTRIBUTION:")
    conf_dist = meta.get('confidence_distribution', {})
    print(f"  High: {conf_dist.get('high', 'N/A')}")
    print(f"  Med:  {conf_dist.get('med', 'N/A')}")
    print(f"  Low:  {conf_dist.get('low', 'N/A')}")
    print(f"  Boosted to High: {conf_dist.get('boosted_to_high', 'N/A')}")
    
    # Sample events by type
    event_types = {}
    for event in events[:100]:  # Sample first 100
        et = event.get('event_type', '<unknown>')
        if et:
            event_types[et] = event_types.get(et, 0) + 1
    
    print(f"\n📋 EVENT TYPES (sample of first 100):")
    for et, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {et:30s}: {count}")
    
    # Entity type distribution
    entity_types = {}
    for cand in candidates:
        et = cand.get('entity_type', '<unknown>')
        entity_types[et] = entity_types.get(et, 0) + 1
    
    print(f"\n🏷️  ENTITY TYPE DISTRIBUTION:")
    for et, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {et:20s}: {count:>4d}")
    
    # Final verdict
    print("\n" + "="*70)
    print("EXPORT VALIDATION SUMMARY")
    print("="*70)
    
    all_good = True
    
    counts = meta.get('counts', {})
    total_events = counts.get('total_events')
    primary_entities = counts.get('primary_entities')
    if total_events is None:
        print("❌ Metadata missing key: counts['total_events']")
        all_good = False
    elif len(events) == total_events:
        print("✅ Events count matches metadata")
    else:
        print(f"❌ Events count mismatch: {len(events)} vs {total_events}")
        all_good = False

    if primary_entities is None:
        print("❌ Metadata missing key: counts['primary_entities']")
        all_good = False
    elif len(candidates) == primary_entities:
        print("✅ Candidates count matches metadata")
    else:
        print(f"❌ Candidates count mismatch: {len(candidates)} vs {primary_entities}")
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
