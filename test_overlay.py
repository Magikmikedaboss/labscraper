#!/usr/bin/env python3
"""Test script to debug seed overlay loading"""

import os
import sys
from pathlib import Path

# Add utils to path
sys.path.append('utils')

from seed_overlay_loader import load_overlay

print(f"Current directory: {os.getcwd()}")
print(f"Files in seeds/overlays: {list(Path('seeds/overlays').glob('*.json'))}")

# Test loading construction overlay
overlay = load_overlay('construction_science', 'seeds/overlays')
print(f"Construction overlay loaded: {overlay is not None}")
if overlay:
    print(f"Overlay keys: {list(overlay.keys())}")
    print(f"Overlay ID: {overlay.get('overlay_id')}")
    print(f"Domain: {overlay.get('domain_id')}")
else:
    print("Overlay not found - checking file existence...")
    from pathlib import Path
    file_path = Path('seeds/overlays/construction_science_aliases.json')
    print(f"File exists: {file_path.exists()}")
    if file_path.exists():
        print(f"File content preview: {file_path.read_text()[:200]}...")