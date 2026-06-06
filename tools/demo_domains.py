#!/usr/bin/env python
"""Test all domains and lenses"""
from utils.run_engine import extract_entities

# Test all available domains
domains = [
    "methods_tooling",
    "construction_science", 
    "neuroscience_cognition",
    "biohacking_longevity",
    "drug_discovery",
    "stem_cells_regen"
]

test_texts = {
    "methods_tooling": "The peptide GGGGSGGGSGGG was tested in mice with LC-MS/MS for stability.",
    "construction_science": "Concrete cracking in foundation due to moisture and freeze-thaw. Steel corrosion observed.",
    "neuroscience_cognition": "IPSC-derived neurons and astrocytes in organoid model. Microglia activation studied.",
    "biohacking_longevity": "The compound extended lifespan in mice. Rapamycin and metformin were tested.",
    "drug_discovery": "The drug candidate showed high binding affinity to the target. IC50 was 10nm.",
    "stem_cells_regen": "Mesenchymal stem cells showed differentiation into osteoblasts."
}

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING ALL DOMAINS")
    print("=" * 60)

    for domain in domains:
        text = test_texts.get(domain, "Test text for " + domain)
        print(f"\n--- {domain} ---")
        print(f"Input: {text}")
        print("Entities:")
        for e in extract_entities(text, domain):
            entity_type = e.get('entity_type', '<unknown>')
            entity_name = e.get('entity_name', '<unknown>')
            print(f"  {entity_type}: {entity_name}")

    # Test lenses
    print("\n" + "=" * 60)
    print("TESTING LENSES")
    print("=" * 60)
    try:
        from lenses import construction_failure_v1
    except (ImportError, ModuleNotFoundError) as e:
        print(f"Error loading lenses: {e}")
    else:
        print("construction_failure_v1 lens loaded")
        print(dir(construction_failure_v1))
