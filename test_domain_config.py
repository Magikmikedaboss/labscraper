#!/usr/bin/env python3
from utils.overlay_scorer import load_domain_config

def test_domain_config():
    try:
        config = load_domain_config('construction_science')
        print(f"✅ Domain config loaded successfully")
        print(f"   Dual lens: {config.get('dual_lens', False)}")
        print(f"   Overlays: {config.get('overlays', [])}")
        print(f"   Name: {config.get('name', 'Unknown')}")
        print(f"   Description: {config.get('description', 'No description')}")
    except Exception as e:
        print(f"❌ Error loading domain config: {e}")

if __name__ == "__main__":
    test_domain_config()