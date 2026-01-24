"""Show v4 export samples"""
import csv
import json

print("="*70)
print("📁 V4 PROFESSIONAL EXPORTS")
print("="*70)

events = []
try:
    with open('output/events_export_v4.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        events = list(reader)
        if not events:
            print('No events found in CSV.')
            if hasattr(reader, 'fieldnames'):
                print('CSV columns:', reader.fieldnames)
        else:
            print("\n✅ events_export_v4.csv: {} events".format(len(events)))
            print("   Columns: {}...".format(', '.join(list(events[0].keys())[:8])))
except FileNotFoundError:
    print('Error: output/events_export_v4.csv not found.')
    events = []
except csv.Error as e:
    print('CSV parsing error: {}'.format(e))
    events = []

# Show high confidence event (safely handle if none exist)
high = next((e for e in events if e.get('confidence_boosted') == 'high'), None)
if high:
    print(f"\n📋 Sample HIGH Confidence Event:")
    print(f"   Event ID: {high.get('event_id', '<missing>')}")
    print(f"   Type: {high.get('event_type', '<missing>')}")
    print(f"   Confidence: {high.get('confidence_original', '<missing>')} → {high.get('confidence_boosted', '<missing>')}")
    print(f"   Primary Entities ({high.get('primary_entity_count', 0)}): {high.get('entities_primary', '')[:100]}...")
    print(f"   Context Entities ({high.get('context_entity_count', 0)}): {high.get('entities_context', '')[:100]}...")
else:
    print(f"\n⚠️  No HIGH confidence events found")
    # Show a medium or low confidence event instead
    sample = events[0] if events else None
    if sample:
        print(f"\n📋 Sample Event (confidence: {sample.get('confidence_boosted', '<missing>')}):")
        print(f"   Event ID: {sample.get('event_id', '<missing>')}")
        print(f"   Type: {sample.get('event_type', '<missing>')}")
        print(f"   Primary Entities ({sample.get('primary_entity_count', 0)}): {sample.get('entities_primary', '')[:100]}...")

# Show candidates (single read, with error handling)
try:
    with open('output/candidates_primary_v4.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)
    print(f"\n✅ candidates_primary_v4.csv: {len(candidates)} entities")
except (FileNotFoundError, IOError) as e:
    print(f'\n❌ Error reading candidates_primary_v4.csv: {e}')
    candidates = []

print(f"\n📊 Top 10 Primary Entities:")
for i, c in enumerate(candidates[:10], 1):
    name = c.get('entity_name')
    etype = c.get('entity_type')
    count = c.get('event_count')
    if name is not None and etype is not None and count is not None:
        print(f"   {i}. {name} ({etype}): {count} events")

meta = {}
try:
    with open('output/run_meta.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)
        print("\n✅ run_meta.json")
except FileNotFoundError:
    print('Error: output/run_meta.json not found.')
    meta = {}
except json.JSONDecodeError as e:
    print('JSON decode error: {}'.format(e))
    meta = {}

# Extract safe variables from meta
total = meta.get('counts', {}).get('total_events', 0)
confidence_distribution = meta.get('confidence_distribution', {})
process_words_demoted = meta.get('process_words_demoted', [])
high_count = confidence_distribution.get('high', 0)
med_count = confidence_distribution.get('med', 0)
low_count = confidence_distribution.get('low', 0)

# Calculate percentages safely
if total > 0:
    high_pct = round(high_count / total * 100, 1)
    med_pct = round(med_count / total * 100, 1)
    low_pct = round(low_count / total * 100, 1)
else:
    high_pct = med_pct = low_pct = 0.0

# Use safe pre-computed variables
print(f"\n📊 Confidence Distribution:")
if total > 0:
    print(f"   High: {high_count} ({high_pct}%)")
    print(f"   Med: {med_count} ({med_pct}%)")
    print(f"   Low: {low_count} ({low_pct}%)")
else:
    print(f"   High: {high_count} (0.0%)")
    print(f"   Med: {med_count} (0.0%)")
    print(f"   Low: {low_count} (0.0%)")

print(f"\n🔧 Process Words Demoted: {', '.join(process_words_demoted[:4])}...")

print("\n" + "="*70)
print("✅ All v4 exports ready in output/ directory!")
print("="*70)
