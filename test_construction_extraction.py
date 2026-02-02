#!/usr/bin/env python3
"""
Test script to verify construction science entity extraction is working correctly.
This script tests the domain-specific entity extraction without running the full scraper.
"""

import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))

try:
    from run_engine import extract_entities
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the peptide-scraper directory")
    sys.exit(1)

def test_construction_entities():
    """Test construction science entity extraction"""
    print("🏗️  Testing Construction Science Entity Extraction")
    print("=" * 60)
    
    # Test sentences with construction entities
    test_sentences = [
        "Concrete samples showed cracking after freeze-thaw cycling",
        "Steel beams experienced corrosion in marine environments",
        "Wood panels were tested for fire resistance and thermal stability",
        "The foundation failed due to moisture infiltration and poor drainage",
        "Glass facades demonstrated excellent weathering performance",
        "Composite materials showed improved fatigue resistance compared to traditional materials",
        "The building collapsed during the earthquake due to structural weaknesses",
        "Insulation materials were evaluated for thermal conductivity and moisture resistance"
    ]
    
    print("Testing construction domain (should extract material, system, environment, failure_mode, hazard, test_method):")
    print()
    
    for i, sentence in enumerate(test_sentences, 1):
        print(f"Test {i}: {sentence}")
        entities = extract_entities(sentence, "construction_science")
        if entities:
            for entity in entities:
                print(f"  ✅ {entity['entity_type']}: {entity['entity_name']} ({entity['role']})")
        else:
            print("  ❌ No entities extracted")
        print()

def test_biomedical_entities():
    """Test biomedical entity extraction for comparison"""
    print("🧪 Testing Biomedical Entity Extraction (for comparison)")
    print("=" * 60)
    
    # Test sentences with biomedical entities
    test_sentences = [
        "The peptide sequence ACDEFGHI showed improved stability in serum",
        "Rapamycin treatment enhanced stem cell differentiation",
        "MTOR inhibition reduced protein synthesis in cancer cells",
        "Organoid models demonstrated better drug response than 2D cultures"
    ]
    
    print("Testing biomedical domain (should extract compound, peptide, target, model, stem_cell):")
    print()
    
    for i, sentence in enumerate(test_sentences, 1):
        print(f"Test {i}: {sentence}")
        entities = extract_entities(sentence, "methods_tooling")  # Default biomedical domain
        if entities:
            for entity in entities:
                print(f"  ✅ {entity['entity_type']}: {entity['entity_name']} ({entity['role']})")
        else:
            print("  ❌ No entities extracted")
        print()

def test_domain_leakage():
    """Test that construction domain doesn't leak biomedical entities"""
    print("🔒 Testing Domain Isolation (No Leakage)")
    print("=" * 60)
    
    # Test that construction domain doesn't extract biomedical entities
    construction_sentence = "Concrete samples showed cracking after freeze-thaw cycling"
    biomedical_entities = extract_entities(construction_sentence, "methods_tooling")  # Biomedical domain
    construction_entities = extract_entities(construction_sentence, "construction_science")  # Construction domain
    
    print(f"Sentence: {construction_sentence}")
    print(f"Biomedical domain entities: {[e['entity_name'] for e in biomedical_entities]}")
    print(f"Construction domain entities: {[e['entity_name'] for e in construction_entities]}")
    print()
    
    # Check for domain leakage
    biomedical_names = {e['entity_name'].lower() for e in biomedical_entities}
    construction_names = {e['entity_name'].lower() for e in construction_entities}
    
    if biomedical_names & construction_names:
        print("❌ DOMAIN LEAKAGE DETECTED: Same entities extracted in both domains")
        print(f"Overlapping entities: {biomedical_names & construction_names}")
    else:
        print("✅ No domain leakage detected - entities are domain-specific")

def main():
    """Run all tests"""
    print("🧪 CONSTRUCTION SCIENCE DOMAIN FIX VERIFICATION")
    print("=" * 60)
    print()
    
    try:
        test_construction_entities()
        print()
        test_biomedical_entities()
        print()
        test_domain_leakage()
        print()
        print("🎉 All tests completed!")
        print()
        print("If construction entities are being extracted correctly, the domain fix is working!")
        print("Next step: Run a clean construction-only scrape to verify end-to-end functionality.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()