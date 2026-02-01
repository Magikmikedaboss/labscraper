#!/usr/bin/env python3
"""
Debug script to check entity validation
"""

import sys
import os
sys.path.append('utils')

from enhanced_entity_extractor import EnhancedEntityExtractor

def debug_validation():
    """Debug entity validation"""
    
    print("=== DEBUGGING ENTITY VALIDATION ===")
    
    extractor = EnhancedEntityExtractor(domain="construction_science")
    
    # Test with concrete
    entity_name = "concrete"
    entity_type = "material"
    
    print(f"Testing entity: {entity_name} (type: {entity_type})")
    
    # Check validation
    is_valid = extractor._is_valid_entity_for_domain(entity_name, entity_type)
    print(f"Is valid for domain: {is_valid}")
    
    # Test with some other entities
    test_entities = [
        ("concrete", "material"),
        ("steel", "material"), 
        ("beam", "system"),
        ("cracking", "failure_mode"),
        ("peptide", "compound"),  # Should be filtered out
        ("protein", "target"),    # Should be filtered out
    ]
    
    print(f"\nTesting multiple entities:")
    for name, type_ in test_entities:
        is_valid = extractor._is_valid_entity_for_domain(name, type_)
        print(f"  {name} ({type_}): {is_valid}")

if __name__ == "__main__":
    debug_validation()