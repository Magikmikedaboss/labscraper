
import json
from pathlib import Path
import datetime


# Check the metadata file
meta_file = Path('output/run_meta_neuroscience_cognition.json')
try:
    with open(meta_file, 'r') as f:
        meta = json.load(f)
except FileNotFoundError:
    print(f"Error: Metadata file '{meta_file}' not found.")
    meta = None
except json.JSONDecodeError:
    print(f"Error: Metadata file '{meta_file}' is not valid JSON.")
    meta = None
except Exception as e:
    print(f"Error opening metadata file '{meta_file}': {e}")
    meta = None

if meta is None:
    exit(1)

print("\n" + "="*70)
print("NEUROSCIENCE RUN INFORMATION")
print("="*70)

from datetime import timezone
timestamp_str = meta.get('timestamp')
if not timestamp_str:
    print("Error: No timestamp in metadata")
    exit(1)
try:
    timestamp = datetime.datetime.fromisoformat(timestamp_str)
except ValueError:
    print(f"Error: Invalid timestamp format: {timestamp_str}")
    exit(1)
if timestamp.tzinfo is None:
    # Assume UTC if no timezone info
    timestamp = timestamp.replace(tzinfo=timezone.utc)
else:
    timestamp = timestamp.astimezone(timezone.utc)
print(f"\nRun ID: {meta.get('run_id', 'Unknown')}")
print(f"Timestamp: {timestamp.strftime('%Y-%m-%d %I:%M:%S %p')}")
print(f"Engine: {meta.get('engine_version', 'Unknown')}")
print(f"Domain: {meta.get('domain_name', 'Unknown')}")

# Calculate how long ago
now = datetime.datetime.now(timezone.utc)
time_diff = now - timestamp
hours_ago = time_diff.total_seconds() / 3600

print(f"\nTime since run: {hours_ago:.1f} hours ago")

if hours_ago > 1:
    print(f"\n⚠️  WARNING: This export is from {hours_ago:.1f} hours ago!")
    print("   If you just ran the scraper, there should be a more recent export.")
else:
    print("\n✅ This export is recent (less than 1 hour old)")

print("\n" + "="*70)
print("EXPORT SUMMARY")
print("="*70)
counts = meta.get('counts', {})
print(f"Total Events: {counts.get('total_events', 0)}")
print(f"Total Entities: {counts.get('total_entities', 0)}")
print(f"Primary Entities: {counts.get('primary_entities', 0)}")
print(f"Context Entities: {counts.get('context_entities', 0)}")

print("\n" + "="*70)
