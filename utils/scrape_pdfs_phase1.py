"""
Phase 1 PDF Scraper Functions
This file contains the core functions needed for PDF processing.
"""

import re
import hashlib
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone
import pdfplumber
from tqdm import tqdm

# Import functions from run_engine.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from run_engine import (
    extract_metadata, chunk_sentences, guess_stage, guess_section,
    extract_entities, extract_quantitative_data,
    detect_method_tags, detect_failure_reason, detect_decision, detect_outcome,
    classify_event_type, evidence_strength, confidence_score,
    suggested_keep, normalize_event_key,
    upsert_source, insert_document, insert_chunk, insert_event,
    link_event_entity, link_event_tag, insert_measurement, upsert_entity,
    now_iso, sha16, sha64, RESEARCH_DOMAIN,
    FAILURE_PHRASES, DECISION_PHRASES, METHOD_TAGS
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