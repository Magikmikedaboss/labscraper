#!/usr/bin/env python3
"""
Test script to verify entity extraction is working correctly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from scrape_pdfs_phase1 import extract_all_entities
from enhanced_entity_extractor import EnhancedEntityExtractor

# Test text with construction science entities
test_text = """
Concrete is a composite material composed of fine and coarse aggregate bonded together with a fluid cement that hardens over time.
Steel reinforcement bars are commonly used to provide tensile strength to concrete structures.
The compressive strength of concrete is typically measured in megapascals (MPa).
"""

print("Testing entity extraction...")
print(f"Test text: {test_text}")
print()

# Test with construction science domain
print("=== Testing with construction_science domain ===")
entities = extract_all_entities(test_text, domain="construction_science")
print(f"Found {len(entities)} entities:")
for entity in entities:
    print(f"  {entity}")

print()

# Test with biomedical domain for comparison
print("=== Testing with biomedical domain ===")
entities_bio = extract_all_entities(test_text, domain="biomedical")
print(f"Found {len(entities_bio)} entities:")
for entity in entities_bio:
    print(f"  {entity}")

print()

# Test the enhanced entity extractor directly
print("=== Testing EnhancedEntityExtractor directly ===")
try:
    extractor = EnhancedEntityExtractor("construction_science")
    entities_enhanced = extractor.extract_entities(test_text, "Test Document")
    print(f"Enhanced extractor found {len(entities_enhanced)} entities:")
    for entity in entities_enhanced:
        print(f"  {entity}")
except Exception as e:
    print(f"Error with enhanced extractor: {e}")
    import traceback
    traceback.print_exc()