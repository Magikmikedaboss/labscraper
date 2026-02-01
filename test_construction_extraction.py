#!/usr/bin/env python3
"""
Test the construction entity extraction function
"""

from utils.scrape_pdfs_phase1 import extract_construction_entities

def test_construction_extraction():
    """Test construction entity extraction"""
    
    # Test construction sentence
    construction_sentence = "The concrete beam showed significant cracking after 5 years of exposure to corrosive environments. The steel reinforcement experienced severe corrosion leading to structural failure."
    
    entities = extract_construction_entities(construction_sentence)
    
    print("Construction sentence entities:")
    for entity in entities:
        print(f"  {entity['entity_type']}: {entity['entity_name']}")
    
    # Test biomedical sentence
    biomedical_sentence = "The compound showed potent activity against the target protein with an IC50 of 10nM. The assay results demonstrated significant inhibition of the pathway in vitro."
    
    entities = extract_construction_entities(biomedical_sentence)
    
    print("\nBiomedical sentence entities (should be empty or minimal):")
    for entity in entities:
        print(f"  {entity['entity_type']}: {entity['entity_name']}")

if __name__ == "__main__":
    test_construction_extraction()