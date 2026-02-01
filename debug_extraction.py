#!/usr/bin/env python3
"""
Debug script to check entity extraction step by step
"""

import sys
import os
sys.path.append('utils')

from enhanced_entity_extractor import EnhancedEntityExtractor
import unicodedata
import re

def debug_extraction():
    """Debug entity extraction step by step"""
    
    print("=== DEBUGGING ENTITY EXTRACTION ===")
    
    extractor = EnhancedEntityExtractor(domain="construction_science")
    test_sentence = "concrete beam cracking"
    
    print(f"Original sentence: '{test_sentence}'")
    
    # Step 1: Check text normalization
    normalized_text = extractor._normalize_text(test_sentence)
    print(f"Normalized text: '{normalized_text}'")
    
    # Step 2: Check seeds loading
    seeds = extractor.seeds
    print(f"Seeds loaded: {len(seeds)} categories")
    print(f"Available categories: {list(seeds.keys())}")
    
    if 'ontology' in seeds and extractor.domain in seeds['ontology']:
        ontology = seeds['ontology'][extractor.domain]
        print(f"Ontology for {extractor.domain}: {list(ontology.keys())}")
        
        # Check materials
        if 'materials' in ontology:
            materials = ontology['materials']
            print(f"Materials: {materials[:10]}...")  # Show first 10
            for material in materials[:10]:
                if material.lower() in normalized_text:
                    print(f"  ✓ Found material '{material}' in text")
                else:
                    print(f"  ✗ Material '{material}' not found in text")
    
    # Step 3: Check abbreviation patterns
    print(f"\nAbbreviation patterns for 'concrete': {extractor.domain_config['abbreviation_map'].get('concrete', [])}")
    
    # Step 4: Test direct entity extraction
    print(f"\n=== TESTING DIRECT EXTRACTION ===")
    try:
        entities = extractor._extract_ontology_entities(test_sentence)
        print(f"Ontology entities: {len(entities)}")
        for entity in entities:
            print(f"  - {entity.entity_type}: {entity.entity_name} (confidence: {entity.confidence})")
    except Exception as e:
        print(f"Error in ontology extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_extraction()