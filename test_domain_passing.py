#!/usr/bin/env python3
"""
Test script to verify domain passing in parallel scraper
"""

import sys
import os
import traceback

# Add the utils directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from scrape_pdfs_phase1 import extract_all_entities
from enhanced_entity_extractor import EnhancedEntityExtractor

def test_domain_extraction():
    """Test that domain is properly passed and used"""
    
    test_sentence = "The concrete beam showed significant cracking after 5 years of exposure to corrosive environments."
    
    print("Testing domain extraction...")
    print(f"Sentence: {test_sentence}")
    print()
    
    # Test with construction_science domain
    print("=== CONSTRUCTION SCIENCE DOMAIN ===")
    try:
        construction_entities = extract_all_entities(test_sentence, "", "construction_science")
        print(f"Construction entities found: {len(construction_entities)}")
        for entity in construction_entities:
            print(f"  - {entity['entity_type']}: {entity['entity_name']} (variant: {entity.get('entity_variant')})")
    except Exception as e:
        traceback.print_exc()
        raise

    print()
    
    # Test with methods_tooling domain
    print("=== METHODS_TOOLING DOMAIN ===")
    try:
        methods_tooling_entities = extract_all_entities(test_sentence, "", "methods_tooling")
        print(f"Methods tooling entities found: {len(methods_tooling_entities)}")
        for entity in methods_tooling_entities:
            print(f"  - {entity['entity_type']}: {entity['entity_name']} (variant: {entity.get('entity_variant')})")
    except Exception as e:
        traceback.print_exc()
        raise

    print()
    
    # Test EnhancedEntityExtractor directly
    print("=== DIRECT ENHANCED ENTITY EXTRACTOR TEST ===")
    try:
        extractor = EnhancedEntityExtractor(domain="construction_science")
        entities = extractor.extract_entities(test_sentence)
        print(f"Direct construction entities: {len(entities)}")
        for entity in entities:
            print(f"  - {entity.entity_type}: {entity.entity_name} (confidence: {entity.confidence})")
    except Exception as e:
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_domain_extraction()