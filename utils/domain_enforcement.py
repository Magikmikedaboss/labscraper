#!/usr/bin/env python3
"""
Domain-specific entity type enforcement to prevent contamination.
"""

# Domain-specific allowed entity types
ALLOWED_ENTITY_TYPES_BY_DOMAIN = {
    "construction_science": {
        "material", "materials",
        "system", "systems", 
        "failure_mode", "failure_modes",
        "environment", "environments",
        "hazard", "hazards",
        "test_method", "test_methods",
        "code", "codes",
        "property", "properties"
    },
    "biohacking_longevity": {
        "peptide", "compound", "target", "pathway", "indication", 
        "model", "stem_cell", "neural_cell", "assay"
    },
    "neuroscience": {
        "peptide", "compound", "target", "pathway", "indication",
        "model", "stem_cell", "neural_cell", "assay"
    },
    "drug_discovery": {
        "peptide", "compound", "target", "pathway", "indication",
        "model", "stem_cell", "neural_cell", "assay"
    },
    "methods_tooling": {
        "peptide", "compound", "target", "pathway", "indication",
        "model", "stem_cell", "neural_cell", "assay"
    }
}

def is_entity_type_allowed_for_domain(entity_type, domain):
    """
    Check if an entity type is allowed for the given domain.
    
    Args:
        entity_type (str): The entity type to check
        domain (str): The research domain
    
    Returns:
        bool: True if allowed, False if should be filtered out
    """
    if domain not in ALLOWED_ENTITY_TYPES_BY_DOMAIN:
        # Unknown domain - allow everything (fallback behavior)
        return True
    
    allowed_types = ALLOWED_ENTITY_TYPES_BY_DOMAIN[domain]
    return entity_type in allowed_types

def filter_entities_for_domain(entities, domain):
    """
    Filter entities to only include those allowed for the domain.
    
    Args:
        entities (list): List of entity dictionaries with 'entity_type' key
        domain (str): The research domain
    
    Returns:
        list: Filtered entities list
    """
    if domain not in ALLOWED_ENTITY_TYPES_BY_DOMAIN:
        # Unknown domain - return all entities (fallback behavior)
        return entities
    
    allowed_types = ALLOWED_ENTITY_TYPES_BY_DOMAIN[domain]
    filtered_entities = []
    
    for entity in entities:
        if entity.get('entity_type') in allowed_types:
            filtered_entities.append(entity)
        else:
            print(f"⚠️  Filtering out entity type '{entity.get('entity_type')}' for domain '{domain}'")
    
    return filtered_entities

def get_contaminated_entity_types(domain):
    """
    Get the list of entity types that should be filtered out for a domain.
    
    Args:
        domain (str): The research domain
    
    Returns:
        set: Entity types that should be filtered out
    """
    if domain not in ALLOWED_ENTITY_TYPES_BY_DOMAIN:
        return set()
    
    all_possible_types = {
        "peptide", "compound", "target", "pathway", "indication",
        "model", "stem_cell", "neural_cell", "assay",
        "material", "materials", "system", "systems",
        "failure_mode", "failure_modes", "environment", "environments",
        "hazard", "hazards", "test_method", "test_methods",
        "code", "codes", "property", "properties"
    }
    
    allowed_types = ALLOWED_ENTITY_TYPES_BY_DOMAIN[domain]
    return all_possible_types - allowed_types

if __name__ == "__main__":
    # Test the enforcement system
    print("🏗️  Construction Science Domain Enforcement Test")
    print("=" * 50)
    
    test_entities = [
        {"entity_type": "material", "name": "concrete"},
        {"entity_type": "pathway", "name": "Wnt"},  # Should be filtered
        {"entity_type": "indication", "name": "cancer"},  # Should be filtered
        {"entity_type": "system", "name": "foundation"},
        {"entity_type": "peptide", "name": "ETELCALCETIDE"},  # Should be filtered
    ]
    
    filtered = filter_entities_for_domain(test_entities, "construction_science")
    
    print(f"Original entities: {len(test_entities)}")
    print(f"Filtered entities: {len(filtered)}")
    print(f"Allowed entities: {[e['name'] for e in filtered]}")
    
    contaminated = get_contaminated_entity_types("construction_science")
    print(f"\nContaminated entity types for construction: {sorted(contaminated)}")