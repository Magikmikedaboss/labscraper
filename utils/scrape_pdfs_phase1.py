"""
Phase 1 PDF Scraper Functions
This file contains the core functions needed for PDF processing.
"""

from pathlib import Path

# Import functions from run_engine.py
import sys
sys.path.insert(0, str(Path(__file__).parent))

from run_engine import (
    extract_entities, confidence_score
)

def confidence_score_phase1(has_entity: bool, method_tags: list[str], failure_reason: str, decision_taken: str, has_measurements: bool, sentence_l: str = "") -> str:
    """Phase 1 confidence scoring function"""
    return confidence_score(has_entity, method_tags, failure_reason, decision_taken, has_measurements, sentence_l)

def extract_all_entities(sentence: str, title: str, domain: str) -> list[dict]:
    """Extract all entities from a sentence based on domain"""
    return extract_entities(sentence, domain)

def main():
    """Main function placeholder"""
    pass

if __name__ == "__main__":
    main()