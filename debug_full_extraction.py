#!/usr/bin/env python3
"""
Debug script to trace through the full ontology extraction function
"""

import sys
import os
sys.path.append('utils')

from enhanced_entity_extractor import EnhancedEntityExtractor
import unicodedata

def debug_full_extraction():
    """Debug the full ontology extraction function step by step"""
    
    print("=== DEBUGGING FULL ONTOLOGY EXTRACTION ===")
    
    extractor = EnhancedEntityExtractor(domain="construction_science")
    test_sentence = "concrete beam cracking"
    
    print(f"Original sentence: '{test_sentence}'")
    
    # Step 1: Normalize text
    text_lower = extractor._normalize_text(test_sentence)
    print(f"Normalized text: '{text_lower}'")
    
    # Step 2: Get seeds
    seeds = extractor.seeds
    if 'ontology' not in seeds or extractor.domain not in seeds['ontology']:
        print("❌ Ontology not found")
        return
    
    ontology = seeds['ontology'][extractor.domain]
    print(f"Ontology loaded for {extractor.domain}")
    
    # Step 3: Get domain config
    domain_config = extractor.domain_config
    print(f"Domain config entity types: {domain_config['entity_types']}")
    
    # Step 4: Extract entities step by step
    entities = []
    
    for entity_type in domain_config['entity_types']:
        print(f"\n--- Checking entity type: {entity_type} ---")
        
        if entity_type not in ontology:
            print(f"  Entity type '{entity_type}' not found in ontology")
            continue
            
        entity_list = ontology[entity_type]
        print(f"  Found {len(entity_list)} entities of type '{entity_type}'")
        
        for entity_name in entity_list[:10]:  # Check first 10
            print(f"    Checking: '{entity_name}'")
            
            # Check exact match
            if entity_name.lower() in text_lower:
                print(f"      ✓ Exact match found")
                
                # Apply domain-specific filtering
                if extractor._is_valid_entity_for_domain(entity_name, entity_type):
                    print(f"      ✓ Passed domain validation")
                    
                    # Create entity
                    entity = {
                        'entity_type': entity_type,
                        'entity_name': entity_name.upper(),
                        'entity_variant': None,
                        'confidence': 0.8,
                        'source': "ontology_exact"
                    }
                    entities.append(entity)
                    print(f"      ✓ Created entity: {entity}")
                else:
                    print(f"      ✗ Failed domain validation")
            else:
                print(f"      ✗ No exact match")
                
            # Check abbreviation variants
            abbrev_map = domain_config.get('abbreviation_map', {})
            if entity_name.lower() in abbrev_map:
                variants = abbrev_map[entity_name.lower()]
                print(f"      Checking variants: {variants}")
                
                for variant in variants:
                    if variant.lower() in text_lower and variant.lower() != entity_name.lower():
                        print(f"        ✓ Found variant: '{variant}'")
                        
                        # Apply domain-specific filtering to variants too
                        if extractor._is_valid_entity_for_domain(variant, entity_type):
                            print(f"        ✓ Variant passed domain validation")
                            
                            entity = {
                                'entity_type': entity_type,
                                'entity_name': entity_name.upper(),
                                'entity_variant': variant.upper(),
                                'confidence': 0.6,
                                'source': "ontology_abbreviation"
                            }
                            entities.append(entity)
                            print(f"        ✓ Created variant entity: {entity}")
                        else:
                            print(f"        ✗ Variant failed domain validation")
                    else:
                        print(f"        ✗ Variant '{variant}' not found")
    
    print(f"\n=== FINAL RESULT ===")
    print(f"Total entities found: {len(entities)}")
    for entity in entities:
        print(f"  - {entity['entity_type']}: {entity['entity_name']} (variant: {entity.get('entity_variant')})")

if __name__ == "__main__":
    debug_full_extraction()