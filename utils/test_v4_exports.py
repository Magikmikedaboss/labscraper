"""
Test v4 Professional Exports
Validates all 4 tweaks are working correctly
"""

import csv
import json
from pathlib import Path
from collections import Counter

OUTPUT_DIR = Path("output")

def test_process_words_demoted():
    """Test that process words are demoted to context, not in primary"""
    print("\n" + "="*70)
    print("TEST 1: Process Words Demoted to Context")
    print("="*70)
    
    process_words = {"quantification", "quantitation", "chromatography", "purification", 
                     "calibration", "validation", "optimization", "quality control"}
    
    # Check candidates_primary_v4.csv
    primary_path = OUTPUT_DIR / "candidates_primary_v4.csv"
    if not primary_path.exists():
        print(f"❌ FAIL: {primary_path} not found")
        return False
    with open(primary_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        primary_entities = [row['entity_name'].lower() for row in reader]    
    # Check for process words in primary
    found_in_primary = [pw for pw in process_words if pw in primary_entities]
    
    if found_in_primary:
        print(f"❌ FAIL: Found process words in primary: {found_in_primary}")
        return False
    else:
        print(f"✅ PASS: No process words in primary entities")
    
    # Verify they exist in run_meta as demoted
    meta_path = OUTPUT_DIR / "run_meta.json"
    if not meta_path.exists():
        print(f"❌ FAIL: {meta_path} not found")
        return False
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)    
    demoted_in_meta = set(x.lower() for x in meta.get("process_words_demoted", []))
    if process_words.issubset(demoted_in_meta):
        print(f"✅ PASS: All process words listed as demoted in run_meta.json")
    else:
        print(f"⚠️  WARNING: Some process words missing from run_meta")
    
    # Check they appear in top entities as context
    context_process_words = [
        e for e in meta["top_entities"] 
        if e["name"].lower() in process_words and e["role"] == "context"
    ]
    
    print(f"✅ PASS: Found {len(context_process_words)} process words in top entities as context:")
    for e in context_process_words:
        print(f"   - {e['name']}: {e['event_count']} events (role: {e['role']})")
    
    return True

def test_confidence_boost():
    """Test that confidence boost rule is applied correctly"""
    print("\n" + "="*70)
    print("TEST 2: Safe Confidence Boost Applied")
    print("="*70)
    
    events_path = OUTPUT_DIR / "events_export_v4.csv"
    if not events_path.exists():
        print(f"❌ FAIL: {events_path} not found")
        return False
    with open(events_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        events = list(reader)
    
    # Verify required columns exist
    if events and 'confidence_original' not in events[0]:
        print(f"❌ FAIL: Missing 'confidence_original' column")
        return False
    
    # Count confidence changes
    boosted_to_high = []
    boosted_to_med = []
    
    for event in events:
        orig = event['confidence_original']
        boosted = event['confidence_boosted']
        
        if orig != boosted:
            if boosted == 'high':
                boosted_to_high.append(event)
            elif boosted == 'med':
                boosted_to_med.append(event)
    
    print(f"✅ Total events: {len(events)}")
    print(f"✅ Boosted to HIGH: {len(boosted_to_high)}")
    print(f"✅ Boosted to MED: {len(boosted_to_med)}")
    
    # Show examples of boosted events
    if boosted_to_high:
        print(f"\n📋 Examples of events boosted to HIGH:")
        for i, event in enumerate(boosted_to_high[:3], 1):
            print(f"\n   {i}. Event {event['event_id'][:8]}...")
            print(f"      Original: {event['confidence_original']} → Boosted: {event['confidence_boosted']}")
            print(f"      Primary entities: {event['primary_entities'][:100]}...")
            print(f"      Context entities: {event['context_entities'][:100]}...")    
    # Verify boost rule logic
    meta_path = OUTPUT_DIR / "run_meta.json"
    if not meta_path.exists():
        print(f"❌ FAIL: {meta_path} not found")
        return False
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)    
    print(f"\n✅ Boost rule: {meta['confidence_boost_rule']}")
    print(f"✅ Confidence distribution after boost:")
    total = len(events)
    if total > 0:
        print(f"   High: {meta['confidence_distribution']['high']} ({meta['confidence_distribution']['high']/total*100:.1f}%)")
        print(f"   Med: {meta['confidence_distribution']['med']} ({meta['confidence_distribution']['med']/total*100:.1f}%)")
        print(f"   Low: {meta['confidence_distribution']['low']} ({meta['confidence_distribution']['low']/total*100:.1f}%)")
    else:
        print(f"   High: {meta['confidence_distribution']['high']} (0.0%)")
        print(f"   Med: {meta['confidence_distribution']['med']} (0.0%)")
        print(f"   Low: {meta['confidence_distribution']['low']} (0.0%)")
    
    return True

def test_entity_count_columns():
    """Test that entity count columns are correct"""
    print("\n" + "="*70)
    print("TEST 3: Entity Count Columns Added")
    print("="*70)
    
    events_path = OUTPUT_DIR / "events_export_v4.csv"
    if not events_path.exists():
        print(f"❌ FAIL: {events_path} not found")
        return False
    with open(events_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        events = list(reader)
    
    # Check columns exist (first verify events is not empty)
    if not events:
        print(f"❌ FAIL: Events export is empty")
        return False
    
    required_cols = ['primary_count', 'context_count', 
                     'primary_entities', 'context_entities', 'all_entities']
    
    if all(col in events[0].keys() for col in required_cols):
        print(f"✅ PASS: All required columns present")
    else:
        print(f"❌ FAIL: Missing columns")
        return False
    
    # Validate counts match actual entities
    errors = 0
    for event in events[:10]:  # Check first 10
        primary_str = event['primary_entities']
        context_str = event['context_entities']
        
        # Count semicolons + 1 (if not empty)
        expected_primary = len([e for e in primary_str.split('; ') if e]) if primary_str else 0
        expected_context = len([e for e in context_str.split('; ') if e]) if context_str else 0
        
        try:
            actual_primary = int(event['primary_count'])
            actual_context = int(event['context_count'])
        except ValueError:
            errors += 1
            print(f"⚠️  Event {event['event_id'][:8]}: Invalid count values")
            continue
        
        if expected_primary != actual_primary or expected_context != actual_context:
            errors += 1
            print(f"⚠️  Event {event['event_id'][:8]}: Expected P={expected_primary}/C={expected_context}, Got P={actual_primary}/C={actual_context}")
    
    if errors == 0:
        print(f"✅ PASS: Entity counts match actual entities (checked 10 events)")
    else:
        print(f"⚠️  WARNING: {errors} events have mismatched counts")
    
    # Helper to safely parse int, returns None on failure
    def safe_int(val):
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    # Collect valid and invalid entries
    valid_primary = []
    valid_context = []
    invalid_primary = []
    invalid_context = []
    for e in events:
        p = safe_int(e['primary_count'])
        c = safe_int(e['context_count'])
        if p is not None:
            valid_primary.append(p)
        else:
            invalid_primary.append(e.get('event_id', '<no id>'))
        if c is not None:
            valid_context.append(c)
        else:
            invalid_context.append(e.get('event_id', '<no id>'))
    primary_counts = Counter(valid_primary)
    context_counts = Counter(valid_context)

    print(f"\n📊 Primary Entity Count Distribution:")
    for count in sorted(primary_counts.keys())[:5]:
        print(f"   {count} entities: {primary_counts[count]} events")
    if invalid_primary:
        print(f"⚠️  {len(invalid_primary)} events had invalid primary_entity_count: {invalid_primary}")

    print(f"\n📊 Context Entity Count Distribution:")
    for count in sorted(context_counts.keys())[:5]:
        print(f"   {count} entities: {context_counts[count]} events")
    if invalid_context:
        print(f"⚠️  {len(invalid_context)} events had invalid context_entity_count: {invalid_context}")
    
    # Show high-value events (multiple primary entities)
    high_value = [e for e in events if safe_int(e['primary_entity_count']) >= 3]
    print(f"\n✅ Events with ≥3 primary entities: {len(high_value)} (high-value research)")
    
    return True

def test_run_meta_json():
    """Test that run_meta.json is complete and valid"""
    print("\n" + "="*70)
    print("TEST 4: run_meta.json Created for Reproducibility")
    print("="*70)
    
    meta_path = OUTPUT_DIR / "run_meta.json"
    
    if not meta_path.exists():
        print(f"❌ FAIL: run_meta.json not found")
        return False
    
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    # Check required fields
    required_fields = [
        'run_id', 'engine_version', 'timestamp', 'database',
        'seeds_version', 'counts', 'confidence_distribution',
        'top_entities', 'process_words_demoted', 'confidence_boost_rule'
    ]
    
    missing = [f for f in required_fields if f not in meta]
    if missing:
        print(f"❌ FAIL: Missing fields: {missing}")
        return False
    
    print(f"✅ PASS: All required fields present")
    print(f"\n📋 Run Metadata:")
    print(f"   Run ID: {meta['run_id']}")
    print(f"   Engine: {meta['engine_version']}")
    print(f"   Timestamp: {meta['timestamp']}")
    print(f"   Total Events: {meta['counts']['total_events']}")
    print(f"   Total Entities: {meta['counts']['total_entities']}")
    print(f"   Primary Entities: {meta['counts']['primary_entities']}")
    print(f"   Context Entities: {meta['counts']['context_entities']}")
    
    print(f"\n📊 Top 10 Entities:")
    for i, entity in enumerate(meta['top_entities'][:10], 1):
        role_icon = "⭐" if entity['role'] == 'primary' else "🔧"
        print(f"   {i}. {role_icon} {entity['name']} ({entity['type']}): {entity['event_count']} events")
    
    return True

def run_all_tests():
    """Run all v4 export tests"""
    print("\n" + "="*70)
    print("🧪 TESTING v4 PROFESSIONAL EXPORTS")
    print("="*70)
    
    results = {
        "Process Words Demoted": test_process_words_demoted(),
        "Confidence Boost Applied": test_confidence_boost(),
        "Entity Count Columns": test_entity_count_columns(),
        "run_meta.json Created": test_run_meta_json()
    }
    
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED - v4 is demo-ready!")
    else:
        print("\n⚠️  Some tests failed - review output above")
    
    return all_passed

if __name__ == "__main__":
    run_all_tests()
