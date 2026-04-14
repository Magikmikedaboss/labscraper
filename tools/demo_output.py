#!/usr/bin/env python
"""Test script to show entity extraction output for all domains"""

from utils.run_engine import (
    extract_entities,
    detect_failure_reason,
    detect_method_tags,
    extract_quantitative_data
)

def render_case(domain, text, show_measurements=False):
    print("=" * 60)
    print(f"DOMAIN: {domain}")
    print("=" * 60)
    print("INPUT:", text.replace("\n", " "))
    print()
    print("ENTITIES:")
    for e in extract_entities(text, domain):
        print(f"  {e['entity_type']}: {e['entity_name']}")
    print()
    print("DETECTION:")
    print(f"  Failure: {detect_failure_reason(text.lower())}")
    print(f"  Method: {detect_method_tags(text.lower())}")
    if show_measurements:
        print(f"  Measurements: {extract_quantitative_data(text)}")

if __name__ == "__main__":
    test1 = """The peptide GGGGSGGGSGGG was tested in mice with LC-MS/MS. 
The compound showed rapid degradation and poor stability. 
We decided to optimize the sequence. 
It was successful with IC50 of 50nm."""
    test2 = """Concrete cracking was observed in the foundation due to moisture 
and freeze-thaw cycles. Steel reinforcement showed corrosion. 
The failure mode was buckling."""
    test3 = """The study used IPSC-derived neurons and astrocytes. 
Microglia activation was observed in the organoid model."""

    render_case("methods_tooling", test1, show_measurements=True)
    print()
    render_case("construction_science", test2)
    print()
    render_case("neuroscience_cognition", test3)
