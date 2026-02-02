#!/usr/bin/env python3
"""
Debug script to check if construction seeds are loaded correctly
"""

import sys
import os
sys.path.append('utils')

from utils.enhanced_entity_extractor import EnhancedEntityExtractor
import json
from pathlib import Path

def debug_seeds():
    """Debug seed loading and entity extraction"""
    
    print("=== DEBUGGING SEED LOADING ===")
    
    # Check if seeds directory exists
    seeds_dir = Path("seeds")
    print(f"Seeds directory exists: {seeds_dir.exists()}")
    
    if seeds_dir.exists():
        print("Files in seeds directory:")
        for file in seeds_dir.iterdir():
            print(f"  - {file.name}")
    
    # Check base directory
    base_dir = seeds_dir / "base"
    print(f"\nBase directory exists: {base_dir.exists()}")
    
    if base_dir.exists():
        print("Ontology directories:")
        for ontology_dir in base_dir.iterdir():
            if ontology_dir.is_dir():
                print(f"  - {ontology_dir.name}")
                for file in ontology_dir.iterdir():
                    print(f"    - {file.name}")
    
    print("\n=== TESTING ENHANCED ENTITY EXTRACTOR ===")
    
    # Test construction extractor
    try:
        extractor = EnhancedEntityExtractor(domain="construction_science")
        print(f"Extractor created for domain: {extractor.domain}")
        print(f"Domain config: {extractor.domain_config}")
        
        # Test with a simple construction sentence
        test_sentence = "concrete beam cracking"
        print(f"\nTesting sentence: '{test_sentence}'")
        
        entities = extractor.extract_entities(test_sentence)
        print(f"Entities found: {len(entities)}")
        for entity in entities:
            print(f"  - {entity.entity_type}: {entity.entity_name} (confidence: {entity.confidence})")
            
    except Exception as e:
        print(f"Error creating extractor: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise the exception to surface it to CI

if __name__ == "__main__":
    debug_seeds()