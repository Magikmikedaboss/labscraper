#!/usr/bin/env python3
"""
Debug script to check ontology entity extraction in detail
"""

import sys
import os
sys.path.append('utils')

from enhanced_entity_extractor import EnhancedEntityExtractor
import unicodedata

def debug_ontology_extraction():
    """Debug ontology entity extraction in detail"""
    
    print("=== DEBUGGING ONTOLOGY EXTRACTION ===")
    
    extractor = EnhancedEntityExtractor(domain="construction_science")
    test_sentence = "concrete beam cracking"
    
    print(f"Original sentence: '{test_sentence}'")
    
    # Step 1: Check text normalization
    normalized_text = extractor._normalize_text(test_sentence)
    print(f"Normalized text: '{normalized_text}'")
    
    # Step 2: Check seeds
    seeds = extractor.seeds
    if 'ontology' in seeds and extractor.domain in seeds['ontology']:
        ontology = seeds['ontology'][extractor.domain]
        print(f"Ontology loaded for {extractor.domain}")
        
        # Step 3: Check materials specifically
        if 'materials' in ontology:
            materials = ontology['materials']
            print(f"Materials count: {len(materials)}")
            print(f"First 5 materials: {materials[:5]}")
            
            # Test each material
            found_entities = []
            for entity_name in materials:
                # Check exact match
                if entity_name.lower() in normalized_text:
                    print(f"✓ Found exact match: '{entity_name}' in '{normalized_text}'")
                    found_entities.append(entity_name)
                else:
                    print(f"✗ No exact match: '{entity_name}' not in '{normalized_text}'")
            
            print(f"Total matches found: {len(found_entities)}")
            
            # Step 4: Check abbreviation variants
            print(f"\nChecking abbreviation variants...")
            abbreviation_map = extractor.domain_config['abbreviation_map']
            for entity_name in materials[:5]:  # Check first 5 materials
                if entity_name.lower() in abbreviation_map:
                    variants = abbreviation_map[entity_name.lower()]
                    print(f"Variants for '{entity_name}': {variants}")
                    for variant in variants:
                        if variant.lower() in normalized_text and variant.lower() != entity_name.lower():
                            print(f"  ✓ Found variant: '{variant}' in '{normalized_text}'")
                        else:
                            print(f"  ✗ Variant '{variant}' not found")
    
    # Step 5: Test the actual function
    print(f"\n=== TESTING _extract_ontology_entities ===")
    try:
        entities = extractor._extract_ontology_entities(test_sentence)
        print(f"Entities returned: {len(entities)}")
        for entity in entities:
            print(f"  - {entity.entity_type}: {entity.entity_name} (confidence: {entity.confidence})")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ontology_extraction()