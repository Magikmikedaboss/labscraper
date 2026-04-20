"""
Phase 1 PDF Scraper Functions
This file contains the core functions needed for PDF processing.
"""


# Import functions from run_engine.py

from utils.run_engine import extract_entities, confidence_score
from utils.event_classification import ConfidenceInput

def confidence_score_phase1(has_entity: bool, method_tags: list[str], failure_reason: str, decision_taken: str, has_measurements: bool, sentence_l: str = "") -> str:
    """Phase 1 confidence scoring function"""
    return confidence_score(
        ConfidenceInput(
            has_entity=has_entity,
            method_tags=method_tags,
            failure_reason=failure_reason,
            decision_taken=decision_taken,
            has_measurements=has_measurements,
            sentence_l=sentence_l
        )
    )

def extract_all_entities(sentence: str, title: str, domain: str) -> list[dict]:
    """Extract all entities from a sentence based on domain"""
    return extract_entities(sentence, domain)

def main():
    """Main function placeholder"""
    pass

if __name__ == "__main__":
    main()