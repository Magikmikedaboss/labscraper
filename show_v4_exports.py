"""Show v4 export samples"""
import csv
import json

print("="*70)
print("📁 V4 PROFESSIONAL EXPORTS")
print("="*70)

# Show events
with open('output/events_export_v4.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    try:
        events = list(reader)
        if not events:
            print('No events found in CSV.')
            if hasattr(reader, 'fieldnames'):
                print('CSV columns:', reader.fieldnames)
        else:
            print(f"\n✅ events_export_v4.csv: {len(events)} events")
            print(f"   Columns: {', '.join(list(events[0].keys())[:8])}...")
    except FileNotFoundError:
        print('Error: output/events_export_v4.csv not found.')
        events = []
    except csv.Error as e:
        print(f'CSV parsing error: {e}')
        events = []

print(f"\n✅ events_export_v4.csv: {len(events)} events")
if events:
    print(f"   Columns: {', '.join(list(events[0].keys())[:8])}...")
else:
    print(f"   No events found in export")

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
try:
    with open('output/candidates_primary_v4.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = [row for row in reader]
except (FileNotFoundError, IOError) as e:
    print(f'Error reading candidates_primary_v4.csv: {e}')
    candidates = []
for i, c in enumerate(candidates[:10], 1):
    name = c.get('entity_name')
    etype = c.get('entity_type')
    count = c.get('event_count')
    if name is not None and etype is not None and count is not None:
        print(f"   {i}. {name} ({etype}): {count} events")

# Show run_meta
with open('output/run_meta.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)
try:
    with open('output/run_meta.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)
except FileNotFoundError:
    print('Error: output/run_meta.json not found.')
    meta = {}
except json.JSONDecodeError as e:
    print(f'JSON decode error: {e}')
    meta = {}
except KeyError as e:
    print(f'Missing key in meta: {e}')
    meta = {}

print(f"\n✅ run_meta.json")
total = meta.get('counts', {}).get('total_events', 0)
print(f"   Total Events: {total}")
if total == 0:
    print('   High Confidence: 0.0%')
    print('   Med Confidence: 0.0%')
    print('   Low Confidence: 0.0%')
else:
    print(f"   High Confidence: {meta.get('confidence_distribution', {}).get('high', 0)} ({meta.get('confidence_distribution', {}).get('high', 0)/total*100:.1f}%)")
    print(f"   Med Confidence: {meta.get('confidence_distribution', {}).get('med', 0)} ({meta.get('confidence_distribution', {}).get('med', 0)/total*100:.1f}%)")
    print(f"   Low Confidence: {meta.get('confidence_distribution', {}).get('low', 0)} ({meta.get('confidence_distribution', {}).get('low', 0)/total*100:.1f}%)")

print(f"\n📊 Confidence Distribution:")
if total > 0:
    print(f"   High: {meta['confidence_distribution']['high']} ({meta['confidence_distribution']['high']/total*100:.1f}%)")
    print(f"   Med: {meta['confidence_distribution']['med']} ({meta['confidence_distribution']['med']/total*100:.1f}%)")
    print(f"   Low: {meta['confidence_distribution']['low']} ({meta['confidence_distribution']['low']/total*100:.1f}%)")
else:
    print(f"   High: {meta['confidence_distribution']['high']} (0.0%)")
    print(f"   Med: {meta['confidence_distribution']['med']} (0.0%)")
    print(f"   Low: {meta['confidence_distribution']['low']} (0.0%)")

print(f"\n🔧 Process Words Demoted: {', '.join(meta.get('process_words_demoted', [])[:4])}...")

print(f"\n✅ run_meta.json")
print(f"   Run ID: {meta['run_id']}")
print(f"   Engine: {meta['engine_version']}")
print(f"   Total Events: {meta['counts']['total_events']}")
print(f"   Primary Entities: {meta['counts']['primary_entities']}")
print(f"   Context Entities: {meta['counts']['context_entities']}")

print(f"\n📊 Confidence Distribution:")
total = meta['counts']['total_events']
if total > 0:
    print(f"   High: {meta['confidence_distribution']['high']} ({meta['confidence_distribution']['high']/total*100:.1f}%)")
    print(f"   Med: {meta['confidence_distribution']['med']} ({meta['confidence_distribution']['med']/total*100:.1f}%)")
    print(f"   Low: {meta['confidence_distribution']['low']} ({meta['confidence_distribution']['low']/total*100:.1f}%)")
else:
    print(f"   High: {meta['confidence_distribution']['high']} (0.0%)")
    print(f"   Med: {meta['confidence_distribution']['med']} (0.0%)")
    print(f"   Low: {meta['confidence_distribution']['low']} (0.0%)")

print(f"\n🔧 Process Words Demoted: {', '.join(meta['process_words_demoted'][:4])}...")

print("\n" + "="*70)
print("✅ All v4 exports ready in output/ directory!")
print("="*70)
