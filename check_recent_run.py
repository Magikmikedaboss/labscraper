
import json
from pathlib import Path
import datetime


# Check the metadata file
meta_file = Path('output/run_meta_neuroscience_cognition.json')
with open(meta_file, 'r') as f:
    meta = json.load(f)

print("\n" + "="*70)
print("NEUROSCIENCE RUN INFORMATION")
print("="*70)

from datetime import timezone
timestamp = datetime.datetime.fromisoformat(meta['timestamp'])
if timestamp.tzinfo is None:
    # Assume UTC if no timezone info
    timestamp = timestamp.replace(tzinfo=timezone.utc)
else:
    timestamp = timestamp.astimezone(timezone.utc)
print(f"\nRun ID: {meta['run_id']}")
print(f"Timestamp: {timestamp.strftime('%Y-%m-%d %I:%M:%S %p')}")
print(f"Engine: {meta['engine_version']}")
print(f"Domain: {meta['domain_name']}")

# Calculate how long ago
now = datetime.datetime.now(timezone.utc)
time_diff = now - timestamp
hours_ago = time_diff.total_seconds() / 3600

print(f"\nTime since run: {hours_ago:.1f} hours ago")

if hours_ago > 1:
    print(f"\n⚠️  WARNING: This export is from {hours_ago:.1f} hours ago!")
    print("   If you just ran the scraper, there should be a more recent export.")
else:
    print(f"\n✅ This export is recent (less than 1 hour old)")

print("\n" + "="*70)
print("EXPORT SUMMARY")
print("="*70)
print(f"Total Events: {meta['counts']['total_events']}")
print(f"Total Entities: {meta['counts']['total_entities']}")
print(f"Primary Entities: {meta['counts']['primary_entities']}")
print(f"Context Entities: {meta['counts']['context_entities']}")

print("\n" + "="*70)
