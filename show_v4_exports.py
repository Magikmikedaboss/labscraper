"""Show v4 export samples"""
import csv
import json

print("="*70)
print("📁 V4 PROFESSIONAL EXPORTS")
print("="*70)

# Show events
with open('output/events_export_v4.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    events = list(reader)

print(f"\n✅ events_export_v4.csv: {len(events)} events")
print(f"   Columns: {', '.join(list(events[0].keys())[:8])}...")

# Show high confidence event (safely handle if none exist)
high = next((e for e in events if e['confidence_boosted'] == 'high'), None)
if high:
    print(f"\n📋 Sample HIGH Confidence Event:")
    print(f"   Event ID: {high['event_id']}")
    print(f"   Type: {high['event_type']}")
    print(f"   Confidence: {high['confidence_original']} → {high['confidence_boosted']}")
    print(f"   Primary Entities ({high['primary_entity_count']}): {high['entities_primary'][:100]}...")
    print(f"   Context Entities ({high['context_entity_count']}): {high['entities_context'][:100]}...")
else:
    print(f"\n⚠️  No HIGH confidence events found")
    # Show a medium or low confidence event instead
    sample = events[0] if events else None
    if sample:
        print(f"\n📋 Sample Event (confidence: {sample['confidence_boosted']}):")
        print(f"   Event ID: {sample['event_id']}")
        print(f"   Type: {sample['event_type']}")
        print(f"   Primary Entities ({sample['primary_entity_count']}): {sample['entities_primary'][:100]}...")

# Show candidates
with open('output/candidates_primary_v4.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    candidates = list(reader)

print(f"\n✅ candidates_primary_v4.csv: {len(candidates)} entities")
print(f"\n📊 Top 10 Primary Entities:")
for i, c in enumerate(candidates[:10], 1):
    print(f"   {i}. {c['entity_name']} ({c['entity_type']}): {c['event_count']} events")

# Show run_meta
with open('output/run_meta.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)

print(f"\n✅ run_meta.json")
print(f"   Run ID: {meta['run_id']}")
print(f"   Engine: {meta['engine_version']}")
print(f"   Total Events: {meta['counts']['total_events']}")
print(f"   Primary Entities: {meta['counts']['primary_entities']}")
print(f"   Context Entities: {meta['counts']['context_entities']}")

print(f"\n📊 Confidence Distribution:")
print(f"   High: {meta['confidence_distribution']['high']} ({meta['confidence_distribution']['high']/meta['counts']['total_events']*100:.1f}%)")
print(f"   Med: {meta['confidence_distribution']['med']} ({meta['confidence_distribution']['med']/meta['counts']['total_events']*100:.1f}%)")
print(f"   Low: {meta['confidence_distribution']['low']} ({meta['confidence_distribution']['low']/meta['counts']['total_events']*100:.1f}%)")

print(f"\n🔧 Process Words Demoted: {', '.join(meta['process_words_demoted'][:4])}...")

print("\n" + "="*70)
print("✅ All v4 exports ready in output/ directory!")
print("="*70)
