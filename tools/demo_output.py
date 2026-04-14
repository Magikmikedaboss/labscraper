#!/usr/bin/env python
"""Test script to show entity extraction output for all domains"""
from utils.run_engine import (
    extract_entities, 
    detect_failure_reason, 
    detect_method_tags,
    extract_quantitative_data
)

if __name__ == "__main__":
    # Test 1: Biomedical / methods_tooling
    test1 = """The peptide GGGGSGGGSGGG was tested in mice with LC-MS/MS. 
The compound showed rapid degradation and poor stability. 
We decided to optimize the sequence. 
It was successful with IC50 of 50nm."""

    print("=" * 60)
    print("DOMAIN: methods_tooling (Biomedical)")
    print("=" * 60)
    print("INPUT:", test1.replace("\n", " "))
    print()
    print("ENTITIES:")
    for e in extract_entities(test1, "methods_tooling"):
        print(f"  {e['entity_type']}: {e['entity_name']}")
    print()
    print("DETECTION:")
    print(f"  Failure: {detect_failure_reason(test1.lower())}")
    print(f"  Method: {detect_method_tags(test1.lower())}")
    print(f"  Measurements: {extract_quantitative_data(test1)}")

    # Test 2: Construction Science
    test2 = """Concrete cracking was observed in the foundation due to moisture 
and freeze-thaw cycles. Steel reinforcement showed corrosion. 
The failure mode was buckling."""

    print()
    print("=" * 60)
    print("DOMAIN: construction_science")
    print("=" * 60)
    print("INPUT:", test2.replace("\n", " "))
    print()
    print("ENTITIES:")
    for e in extract_entities(test2, "construction_science"):
        print(f"  {e['entity_type']}: {e['entity_name']}")
    print()
    print("DETECTION:")
    print(f"  Failure: {detect_failure_reason(test2.lower())}")
    print(f"  Method: {detect_method_tags(test2.lower())}")


    # Test 3: Neuroscience
    test3 = """The study used IPSC-derived neurons and astrocytes. 
Microglia activation was observed in the organoid model."""

    print()
    print("=" * 60)
    print("DOMAIN: neuroscience_cognition")
    print("=" * 60)
    print("INPUT:", test3.replace("\n", " "))
    print()
    print("ENTITIES:")
    for e in extract_entities(test3, "neuroscience_cognition"):
        print(f"  {e['entity_type']}: {e['entity_name']}")
    print()
    print("DETECTION:")
    print(f"  Failure: {detect_failure_reason(test3.lower())}")
    print(f"  Method: {detect_method_tags(test3.lower())}")
