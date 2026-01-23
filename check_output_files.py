import os
from pathlib import Path
import datetime

output_dir = Path('output')
files = []

for f in output_dir.iterdir():
    if f.is_file():
        stat = f.stat()
        files.append({
            'name': f.name,
            'size': stat.st_size,
            'modified': datetime.datetime.fromtimestamp(stat.st_mtime)
        })

files.sort(key=lambda x: x['modified'], reverse=True)

print("\n" + "="*80)
print("OUTPUT FOLDER FILES (sorted by most recent)")
print("="*80)

for f in files:
    size_kb = f['size'] / 1024
    print(f"{f['name']:50s} {f['modified'].strftime('%Y-%m-%d %H:%M:%S')} {size_kb:>10.1f} KB")

print("\n" + "="*80)
print(f"Total files: {len(files)}")
print("="*80)
