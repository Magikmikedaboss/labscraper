"""
Phase 1 PDF Scraper Functions - Full Version
This file contains all the core functions needed for the parallel PDF processing.
"""

import re
import hashlib
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple, Set

# Import from run_engine.py
import sys
sys.path.insert(0, str(Path(__file__).parent))

from run_engine import (
    extract_entities, confidence_score, extract_metadata
)

# Constants and patterns from run_engine.py
FAILURE_PHRASES = {
    "stability_failure": ["rapidly degraded", "degraded", "unstable", "poor stability", "short half-life"],
    "no_activity": ["no significant", "no measurable", "did not show", "no activity", "inactive"],
    "toxicity_flag": ["cytotoxic", "toxicity", "cell death"],
    "reproducibility": ["reproducible", "reproducibility", "batch-to-batch", "variability"],
    "scalability": ["scale-up", "scalable", "manufacturing", "yield", "process", "costly to produce"],
    "regulatory": ["regulatory", "guideline", "compliance", "safety concern", "risk assessment"],
}

DECISION_PHRASES = {
    "abandoned": ["not pursued", "not pursued further", "excluded", "discarded"],
    "modified": ["optimized", "modified", "analog", "derivative", "cyclized", "pegylated", "amidated"],
    "continued": ["further study", "continued", "follow-up", "subsequently", "next we"],
    "paused": ["inconclusive", "unclear", "requires further investigation"],
    "replicated": ["replicated", "repeated", "validated"],
    "escalated": ["advanced to", "moved to", "in vivo", "clinical"],
}

METHOD_TAGS = {
    "lc-ms/ms": ["lc-ms/ms", "lc ms/ms", "lc-ms", "mass spectrometry", "ms/ms"],
    "fluorescent": ["fluorescent", "fluorescence", "fluorophore", "label"],
    "serum": ["serum", "plasma", "biological fluids"],
    "incubation": ["incubation", "long incubation"],
    "nitrosamine": ["nitrosamine", "nitrosamines"],
    "gmp": ["gmp", "good manufacturing practice"],
}

def sha16(s: str) -> str:
    """Generate 16-character SHA256 hash"""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def sha64(s: str) -> str:
    """Generate full SHA256 hash"""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def chunk_sentences(text: str) -> List[str]:
    """Split text into sentences"""
    parts = re.split(r"(?<=[\.\?\!])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]

def guess_stage(sentence_l: str) -> str:
    """Guess study stage from sentence"""
    if any(k in sentence_l for k in ["in vivo", "mouse", "rat", "animal model"]):
        return "in_vivo"
    if any(k in sentence_l for k in ["in vitro", "cell line", "cells", "culture"]):
        return "in_vitro"
    if any(k in sentence_l for k in ["clinical", "patients", "phase i", "phase ii", "randomized"]):
        return "clinical"
    return "unknown"

def guess_section(page_text_l: str) -> str:
    """Guess document section from page text"""
    if "methods" in page_text_l and "results" in page_text_l:
        return "mixed"
    if "methods" in page_text_l:
        return "methods"
    if "results" in page_text_l:
        return "results"
    if "discussion" in page_text_l:
        return "discussion"
    return "unknown"

def extract_all_entities(sentence: str, title: str, domain: str) -> List[Dict]:
    """Extract all entities from a sentence based on domain"""
    return extract_entities(sentence, domain)

def extract_quantitative_data(sentence: str) -> List[Dict]:
    """Extract numerical measurements from sentence"""
    QUANTITATIVE_PATTERNS = [
        (r'ic50.*?(\d+\.?\d*)\s*(nm|μm|mm|µm)', 'ic50'),
        (r'ec50.*?(\d+\.?\d*)\s*(nm|μm|mm|µm)', 'ec50'),
        (r'kd.*?(\d+\.?\d*)\s*(nm|μm|mm|µm)', 'kd'),
        (r'ki.*?(\d+\.?\d*)\s*(nm|μm|mm|µm)', 'ki'),
        (r'half[- ]?life.*?(\d+\.?\d*)\s*(min|hour|day|hr|h)', 'half_life'),
        (r'stability.*?(\d+\.?\d*)\s*(%|percent)', 'stability_percent'),
        (r't1/2.*?(\d+\.?\d*)\s*(min|hour|day|hr|h)', 'half_life'),
    ]
    
    measurements = []
    s_l = sentence.lower()
    
    for pattern, mtype in QUANTITATIVE_PATTERNS:
        matches = re.finditer(pattern, s_l)
        for m in matches:
            try:
                value = float(m.group(1))
                unit = m.group(2)
                measurements.append({
                    'measurement_type': mtype,
                    'value': value,
                    'unit': unit,
                    'context': m.group(0)
                })
            except (ValueError, IndexError):
                continue
    
    return measurements

def detect_method_tags(sentence_l: str) -> List[str]:
    """Detect method tags in sentence"""
    tags = []
    for tag, phrases in METHOD_TAGS.items():
        if any(p in sentence_l for p in phrases):
            tags.append(tag)
    return tags

def detect_failure_reason(sentence_l: str) -> str:
    """Detect failure reason from sentence"""
    for reason, phrases in FAILURE_PHRASES.items():
        if any(p in sentence_l for p in phrases):
            if reason == "reproducibility":
                return "reproducibility"
            if reason == "scalability":
                return "scalability"
            if reason == "regulatory":
                return "regulatory"
            return reason
    return "unknown"

def detect_decision(sentence_l: str) -> Tuple[str, str | None]:
    """Detect decision from sentence"""
    for decision, phrases in DECISION_PHRASES.items():
        if any(p in sentence_l for p in phrases):
            return decision, None
    return "unknown", None

def detect_outcome(sentence_l: str) -> str:
    """Detect outcome from sentence"""
    OUTCOME_PHRASES = {
        "failed": ["no significant", "no measurable", "inactive", "excluded", "not pursued"],
        "improved": ["improved", "increased", "enhanced", "more stable", "longer half-life"],
        "successful": ["significant", "potent", "strong activity"],
        "weak": ["weak", "limited"],
        "moderate": ["moderate"],
    }
    
    for outcome in ["failed", "improved", "successful", "moderate", "weak"]:
        if any(p in sentence_l for p in OUTCOME_PHRASES[outcome]):
            return outcome
    return "unknown"

def classify_event_type(sentence_l: str, method_tags: List[str], failure_reason: str, decision_taken: str) -> str:
    """Classify event type from sentence and context"""
    if "nitrosamine" in method_tags or failure_reason == "regulatory":
        return "regulatory_risk"
    if failure_reason == "toxicity_flag":
        return "toxicity_flag"
    if failure_reason == "stability_failure":
        return "stability_issue"
    if failure_reason == "no_activity" or any(k in sentence_l for k in ["activity", "efficacy", "potent", "ic50", "ec50"]):
        return "efficacy_result"
    if failure_reason == "scalability" or any(k in sentence_l for k in ["manufacturing", "scale-up", "yield"]):
        return "manufacturing_constraint"
    if method_tags:
        if any(k in sentence_l for k in ["cost-intensive", "expensive", "time-consuming", "fast", "cost-effective"]):
            return "cost_tradeoff"
        return "method_evaluation"
    if decision_taken != "unknown":
        return "decision_point"
    return "other"

def evidence_strength(sentence_l: str) -> str:
    """Determine evidence strength from sentence"""
    if any(k in sentence_l for k in ["we conclude", "demonstrate", "significant", "robust", "strong"]):
        return "strong"
    if any(k in sentence_l for k in ["suggest", "may", "might", "could", "trend"]):
        return "weak"
    return "moderate"

def confidence_score_phase1(has_entity: bool, method_tags: List[str], failure_reason: str, decision_taken: str, has_measurements: bool, sentence_l: str = "") -> str:
    """Phase 1 confidence scoring function"""
    return confidence_score(has_entity, method_tags, failure_reason, decision_taken, has_measurements, sentence_l)

def suggested_keep(conf: str, event_type: str, failure_reason: str, decision_taken: str, tags: List[str]) -> int:
    """Determine if event should be kept based on confidence and context"""
    if conf in ("med", "high"):
        return 1
    if event_type not in ("other",) and (failure_reason != "unknown" or decision_taken != "unknown" or tags):
        return 1
    return 0

def normalize_event_key(event_type: str, entities: List[Dict], page: int, snippet: str) -> str:
    """Create key for deduplication"""
    entity_str = "|".join(sorted(e['entity_name'] for e in entities))
    snippet_hash = sha16(snippet[:100])
    return f"{event_type}|{entity_str}|{page}|{snippet_hash}"

# Database functions
def upsert_source(con, source_id: str, pdf_file: str, metadata: Dict):
    """Insert or update source record"""
    con.execute(
        """INSERT OR IGNORE INTO sources(source_id, pdf_file, title, authors, year, doi, imported_at)
           VALUES (?,?,?,?,?,?,?)""",
        (source_id, pdf_file, metadata.get('title'), metadata.get('authors'), 
         metadata.get('year'), metadata.get('doi'), "2026-02-07T00:00:00Z"),
    )

def insert_document(con, source_id: str, file_path: str, sha256: str) -> str:
    """Insert document record"""
    doc_id = sha16(f"{source_id}|{file_path}|{sha256}")
    con.execute(
        """INSERT OR IGNORE INTO documents(doc_id, source_id, file_path, file_type, sha256, created_at)
           VALUES (?,?,?,?,?,?)""",
        (doc_id, source_id, file_path, "pdf", sha256, "2026-02-07T00:00:00Z"),
    )
    return doc_id

def insert_chunk(con, source_id: str, doc_id: str, page_number: int, section_guess: str, chunk_text: str) -> str:
    """Insert chunk record"""
    chunk_id = sha16(f"{doc_id}|{page_number}|{chunk_text[:200]}")
    con.execute(
        """INSERT OR IGNORE INTO chunks(chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, "2026-02-07T00:00:00Z"),
    )
    return chunk_id

def insert_event(con, source_id: str, doc_id: str, chunk_id: str, page_number: int,
                 domain: str, event_type: str, study_stage: str, biological_system: str | None, application_area: str | None,
                 outcome: str, failure_reason: str, decision_taken: str, decision_driver: str | None,
                 evidence_snippet: str, evidence_strength_v: str, confidence_v: str) -> str:
    """Insert research event record"""
    base = f"{source_id}|{doc_id}|{page_number}|{event_type}|{evidence_snippet[:180]}"
    event_id = sha16(base)
    con.execute(
        """INSERT OR IGNORE INTO research_events(
             event_id, research_domain, event_type, study_stage, biological_system, application_area,
             outcome, failure_reason, decision_taken, decision_driver,
             evidence_snippet, evidence_strength, confidence,
             source_id, doc_id, chunk_id, page_number, created_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event_id, domain, event_type, study_stage, biological_system, application_area,
            outcome, failure_reason, decision_taken, decision_driver,
            evidence_snippet[:500], evidence_strength_v, confidence_v,
            source_id, doc_id, chunk_id, page_number, "2026-02-07T00:00:00Z"
        ),
    )
    return event_id

def link_event_entity(con, event_id: str, entity_id: str, role: str):
    """Link event to entity"""
    con.execute(
        """INSERT OR IGNORE INTO event_entities(event_id, entity_id, role)
           VALUES (?,?,?)""",
        (event_id, entity_id, role),
    )

def link_event_tag(con, event_id: str, tag: str):
    """Link event to tag"""
    con.execute("INSERT OR IGNORE INTO tags(tag) VALUES(?)", (tag,))
    con.execute(
        """INSERT OR IGNORE INTO event_tags(event_id, tag)
           VALUES (?,?)""",
        (event_id, tag),
    )

def insert_measurement(con, event_id: str, measurement: Dict):
    """Insert quantitative measurement"""
    measurement_id = sha16(f"{event_id}|{measurement['measurement_type']}|{measurement['value']}|{measurement['unit']}")
    con.execute(
        """INSERT OR IGNORE INTO quantitative_measurements(
             measurement_id, event_id, measurement_type, value, unit, context, created_at
           ) VALUES (?,?,?,?,?,?,?)""",
        (measurement_id, event_id, measurement['measurement_type'], 
         measurement['value'], measurement['unit'], measurement['context'], "2026-02-07T00:00:00Z"),
    )

def upsert_entity(con, entity_type: str, entity_name: str, entity_variant: str | None, organism: str | None) -> str:
    """Insert or update entity record"""
    key = f"{entity_type}|{entity_name}|{entity_variant or ''}|{organism or ''}"
    entity_id = sha16(key)
    con.execute(
        """INSERT OR IGNORE INTO entities(entity_id, entity_type, entity_name, entity_variant, organism, created_at)
           VALUES (?,?,?,?,?,?)""",
        (entity_id, entity_type, entity_name, entity_variant, organism, "2026-02-07T00:00:00Z"),
    )
    return entity_id

def main():
    """Main function placeholder"""
    pass

if __name__ == "__main__":
    main()