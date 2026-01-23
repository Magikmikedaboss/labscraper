"""
Phase 1 Enhancement: Improved Entity Coverage
- Adds assay/method extraction
- Adds pathway extraction  
- Adds indication extraction
- Improves entity-event linking
- Target: 70%+ entity coverage (up from 13%)
"""

import re
import hashlib
import sqlite3
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import pdfplumber
from tqdm import tqdm

# Import the new entity extractor
from entity_extractor import load_seeds, extract_entities as extract_new_entities, score_event_confidence

# Default paths (can be overridden via CLI)
DB_PATH = Path("output") / "peptide_intel.sqlite"
INPUT_DIR = Path("input_pdfs")
RESEARCH_DOMAIN = "peptide"

# Load JSON seeds for new entity types
SEEDS = load_seeds("seeds")

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def sha64(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def chunk_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[\.\?\!])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts if p.strip()]

def guess_stage(sentence_l: str) -> str:
    if any(k in sentence_l for k in ["in vivo", "mouse", "rat", "animal model"]):
        return "in_vivo"
    if any(k in sentence_l for k in ["in vitro", "cell line", "cells", "culture"]):
        return "in_vitro"
    if any(k in sentence_l for k in ["clinical", "patients", "phase i", "phase ii", "randomized"]):
        return "clinical"
    return "unknown"

def guess_section(page_text_l: str) -> str:
    if "methods" in page_text_l and "results" in page_text_l:
        return "mixed"
    if "methods" in page_text_l:
        return "methods"
    if "results" in page_text_l:
        return "results"
    if "discussion" in page_text_l:
        return "discussion"
    return "unknown"

# ---------------------------------------------------------
# Metadata Extraction
# ---------------------------------------------------------
def extract_metadata(pdf_path: Path, pdf) -> dict:
    """Extract paper metadata from PDF"""
    metadata = {
        'title': None,
        'authors': None,
        'year': None,
        'doi': None,
        'venue': None
    }
    
    if pdf.metadata:
        metadata['title'] = pdf.metadata.get('Title')
        metadata['authors'] = pdf.metadata.get('Author')
        
        if pdf.metadata.get('CreationDate'):
            try:
                year_match = re.search(r'(19|20)\d{2}', str(pdf.metadata.get('CreationDate')))
                if year_match:
                    metadata['year'] = int(year_match.group(0))
            except:
                pass
    
    if pdf.pages:
        try:
            first_page = pdf.pages[0].extract_text() or ""
            
            doi_match = re.search(r'doi[:\s]*(10\.\d{4,}/[^\s]+)', first_page, re.I)
            if doi_match:
                metadata['doi'] = doi_match.group(1).rstrip('.,;')
            
            if not metadata['year']:
                year_match = re.search(r'\b(19|20)\d{2}\b', first_page)
                if year_match:
                    metadata['year'] = int(year_match.group(0))
            
            if not metadata['title']:
                lines = first_page.split('\n')[:10]
                for line in lines:
                    if len(line) > 20 and len(line) < 200:
                        metadata['title'] = line.strip()
                        break
        except Exception as e:
            print(f"  ⚠️  Could not extract metadata from first page: {e}")
    
    return metadata

# ---------------------------------------------------------
# Seed File Loading (TXT format for existing seeds)
# ---------------------------------------------------------
def load_seed_file(filepath: Path) -> set:
    """Load seed list from file, ignoring comments and empty lines"""
    seeds = set()
    if not filepath.exists():
        print(f"  ⚠️  Seed file not found: {filepath}")
        return seeds
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                seeds.add(line.lower())
    
    return seeds

# Load existing TXT seed files
SEEDS_DIR = Path("seeds")
COMPOUND_SEED_LIST = load_seed_file(SEEDS_DIR / "compounds.txt")
TARGET_SEED_LIST = load_seed_file(SEEDS_DIR / "targets.txt")
MODEL_SEED_LIST = load_seed_file(SEEDS_DIR / "models.txt")
STOPWORD_SEED_LIST = load_seed_file(SEEDS_DIR / "stopwords.txt")

print(f"📋 Loaded TXT seeds:")
print(f"   Compounds: {len(COMPOUND_SEED_LIST)}")
print(f"   Targets: {len(TARGET_SEED_LIST)}")
print(f"   Models: {len(MODEL_SEED_LIST)}")
print(f"   Stopwords: {len(STOPWORD_SEED_LIST)}")

print(f"📋 Loaded JSON seeds:")
print(f"   Assays: {len(SEEDS.get('assays', {}).get('assays', []))}")
print(f"   Pathways: {len(SEEDS.get('pathways', {}).get('pathways', []))}")
print(f"   Indications: {len(SEEDS.get('indications', {}).get('indications', []))}")
print(f"   Neural Cells: {len(SEEDS.get('neural_cells', {}).get('neural_cells', []))}")

# ---------------------------------------------------------
# Peptide/Sequence Extraction (existing logic)
# ---------------------------------------------------------
SEQUENCE_PRESENTATION_PATTERNS = [
    r'sequence[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
    r'seq[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
    r'peptide[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
    r'residues?\s+\d+[-–]\d+[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
    r'[Nn]-terminus[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
    r'[Cc]-terminus[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
    r'\(([ACDEFGHIKLMNPQRSTVWY]{8,100})\)',
    r'\[([ACDEFGHIKLMNPQRSTVWY]{8,100})\]',
]

FAKE_SEQUENCE_STOPLIST = {
    "MALDI", "FTICR", "HPLC", "LCMS", "LCMSMS", "MSMS",
    "UVVIS", "SDS", "PAGE", "NMR", "ELISA", "DNA", "RNA", "PCR",
    "PEPTIDE", "PEPTIDES", "SEQUENCE", "SEQUENCES", "RESIDUES",
    "CLINICAL", "TERMINAL", "MATERIALS", "RESEARCH", "ANALYSIS",
    "DEGRADATI", "DEGRADATION", "SYNTHESIS", "HARMLESS", "AMPHIPHILES",
    "AFFINITY", "REMAINING", "INCREASED", "ANDVICEVERSA", "INITIALLY",
    "ALDEHYDES", "CHEMISTS", "CLEAVAGE", "SEGMENTS",
}

KNOWN_PEPTIDES = {
    "ETELCALCETIDE", "PLECANATIDE", "TERIPARATIDE", "KYNETWRSED",
    "OCTREOTIDE", "LANREOTIDE", "PASIREOTIDE", "SOMATOSTATIN",
}

STEM_CELL_KEYWORDS = [
    "msc", "mesenchymal", "ipsc", "pluripotent", "stem cell", "stem-cell",
    "organoid", "differentiation", "reprogramming"
]

def is_split_word(seq: str, sentence: str) -> bool:
    """Check if sequence looks like it was chopped from a larger English word"""
    seq_upper = seq.upper()
    idx = sentence.upper().find(seq_upper)
    
    if idx == -1:
        return False
    
    before_idx = idx - 1
    after_idx = idx + len(seq_upper)
    
    if before_idx >= 0 and sentence[before_idx].isalpha():
        return True
    if after_idx < len(sentence) and sentence[after_idx].isalpha():
        return True
    
    return False

def extract_presented_sequences(sentence: str) -> list[str]:
    """Extract sequences that are explicitly presented in the sentence"""
    sequences = []
    
    for pattern in SEQUENCE_PRESENTATION_PATTERNS:
        matches = re.finditer(pattern, sentence, re.IGNORECASE)
        for match in matches:
            seq = match.group(1).upper()
            sequences.append(seq)
    
    return list(set(sequences))

def is_probable_peptide(seq: str, sentence: str = "") -> bool:
    """Light validation - simple and future-proof"""
    s = seq.upper().strip()
    
    if s in KNOWN_PEPTIDES:
        return True
    
    if s in FAKE_SEQUENCE_STOPLIST:
        return False
    
    if len(s) < 8 or len(s) > 100:
        return False
    
    if len(set(s)) < 4:
        return False
    
    if sentence and is_split_word(s, sentence):
        return False
    
    return True

# ---------------------------------------------------------
# PHASE 1: Enhanced Entity Extraction
# ---------------------------------------------------------
def extract_all_entities(sentence: str, title: str = "") -> list[dict]:
    """
    PHASE 1: Extract ALL entity types including new ones
    
    Returns list of {entity_type, entity_name, entity_variant, role}
    
    Entity types:
    - compound: drug/molecule names
    - peptide: literal sequences
    - target: biological targets
    - model: experimental systems
    - stem_cell: stem cell markers
    - assay: methods/assays (NEW)
    - pathway: signaling pathways (NEW)
    - indication: diseases/conditions (NEW)
    """
    ents = []
    s_l = sentence.lower()
    extracted_names = set()
    
    # Combine title + sentence for better context
    combined_text = f"{title}\n{sentence}" if title else sentence
    
    # 1) COMPOUND: Drug/molecule names (PRIORITY)
    for compound in COMPOUND_SEED_LIST:
        if re.search(r'\b' + re.escape(compound) + r'\b', s_l):
            name = compound.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "compound",
                    "entity_name": name,
                    "entity_variant": "drug",
                    "role": "tested"
                })
                extracted_names.add(name)
    
    # 2) PEPTIDE SEQUENCES: Only if NOT already a compound
    presented_seqs = extract_presented_sequences(sentence)
    for seq in presented_seqs:
        if is_probable_peptide(seq, sentence) and seq not in extracted_names:
            ents.append({
                "entity_type": "peptide",
                "entity_name": seq,
                "entity_variant": None,
                "role": "tested"
            })
            extracted_names.add(seq)
    
    # 3) TARGET: Biological targets
    for target in TARGET_SEED_LIST:
        if re.search(r'\b' + re.escape(target) + r'\b', sentence, re.IGNORECASE):
            name = target.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "target",
                    "entity_name": name,
                    "entity_variant": "protein",
                    "role": "target"
                })
                extracted_names.add(name)
    
    # 4) MODEL: Experimental systems
    for model in MODEL_SEED_LIST:
        if re.search(r'\b' + re.escape(model) + r'\b', s_l):
            name = model.upper() if model.isupper() or len(model) <= 5 else model.capitalize()
            if name not in extracted_names:
                # Determine variant
                variant = "unknown"
                if model in ["mouse", "mice", "rat", "rats", "human", "humans"]:
                    variant = "organism"
                elif model in ["serum", "plasma", "blood", "csf", "urine"]:
                    variant = "biofluid"
                elif "organoid" in model or "spheroid" in model:
                    variant = "3d_model"
                elif any(char.isdigit() for char in model):
                    variant = "cell_line"
                
                ents.append({
                    "entity_type": "model",
                    "entity_name": name,
                    "entity_variant": variant,
                    "role": "model"
                })
                extracted_names.add(name)
    
    # 5) STEM_CELL: Stem cell keywords
    for k in STEM_CELL_KEYWORDS:
        if k in s_l:
            name = k.upper() if k in ["msc", "ipsc"] else k
            if name not in extracted_names:
                ents.append({
                    "entity_type": "stem_cell",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "tested"
                })
                extracted_names.add(name)
    
    # 6) NEURAL_CELL: Neural cell types (NEW - PRIMARY NEUROSCIENCE ENTITIES)
    neural_cells_data = SEEDS.get("neural_cells", {})
    for neural_cell in neural_cells_data.get("neural_cells", []):
        # Use word boundary for better matching
        if re.search(r'\b' + re.escape(neural_cell.lower()) + r'\b', s_l):
            if neural_cell not in extracted_names:
                ents.append({
                    "entity_type": "neural_cell",
                    "entity_name": neural_cell,
                    "entity_variant": "cell_type",
                    "role": "tested"
                })
                extracted_names.add(neural_cell)
    
    # 7) ASSAY: Methods/assays (NEW - PHASE 1)
    assays_data = SEEDS.get("assays", {})
    for assay in assays_data.get("assays", []):
        # Use word boundary for better matching
        if re.search(r'\b' + re.escape(assay.lower()) + r'\b', s_l):
            if assay not in extracted_names:
                ents.append({
                    "entity_type": "assay",
                    "entity_name": assay,
                    "entity_variant": "assay",
                    "role": "method"
                })
                extracted_names.add(assay)
    
    # Also extract metrics as assays (with word boundaries)
    for metric in assays_data.get("metrics", []):
        # Use word boundary to prevent "Ki" matching "kinase"
        if re.search(r'\b' + re.escape(metric.lower()) + r'\b', s_l):
            if metric not in extracted_names:
                ents.append({
                    "entity_type": "assay",
                    "entity_name": metric,
                    "entity_variant": "metric",
                    "role": "measurement"
                })
                extracted_names.add(metric)
    
    # 8) PATHWAY: Signaling pathways (NEW - PHASE 1)
    pathways_data = SEEDS.get("pathways", {})
    for pathway in pathways_data.get("pathways", []):
        # Use word boundary for better matching
        if re.search(r'\b' + re.escape(pathway.lower()) + r'\b', s_l):
            if pathway not in extracted_names:
                ents.append({
                    "entity_type": "pathway",
                    "entity_name": pathway,
                    "entity_variant": "pathway",
                    "role": "mechanism"
                })
                extracted_names.add(pathway)
    
    # 9) INDICATION: Diseases/conditions (NEW - PHASE 1)
    indications_data = SEEDS.get("indications", {})
    for indication in indications_data.get("indications", []):
        # Use word boundary for better matching
        if re.search(r'\b' + re.escape(indication.lower()) + r'\b', s_l):
            if indication not in extracted_names:
                ents.append({
                    "entity_type": "indication",
                    "entity_name": indication,
                    "entity_variant": "disease",
                    "role": "indication"
                })
                extracted_names.add(indication)
    
    return ents

# ---------------------------------------------------------
# Quantitative Data Extraction
# ---------------------------------------------------------
QUANTITATIVE_PATTERNS = [
    (r'ic50.*?(\d+\.?\d*)\s*(nm|μm|mm|µm)', 'ic50'),
    (r'ec50.*?(\d+\.?\d*)\s*(nm|μm|mm|µm)', 'ec50'),
    (r'kd.*?(\d+\.?\d*)\s*(nm|μm|mm|µm)', 'kd'),
    (r'ki.*?(\d+\.?\d*)\s*(nm|μm|mm|µm)', 'ki'),
    (r'half[- ]?life.*?(\d+\.?\d*)\s*(min|hour|day|hr|h)', 'half_life'),
    (r'stability.*?(\d+\.?\d*)\s*(%|percent)', 'stability_percent'),
    (r't1/2.*?(\d+\.?\d*)\s*(min|hour|day|hr|h)', 'half_life'),
]

def extract_quantitative_data(sentence: str) -> list[dict]:
    """Extract numerical measurements from sentence"""
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

# ---------------------------------------------------------
# Event classification rules
# ---------------------------------------------------------
METHOD_TAGS = {
    "lc-ms/ms": ["lc-ms/ms", "lc ms/ms", "lc-ms", "mass spectrometry", "ms/ms"],
    "fluorescent": ["fluorescent", "fluorescence", "fluorophore", "label"],
    "serum": ["serum", "plasma", "biological fluids"],
    "incubation": ["incubation", "long incubation"],
    "nitrosamine": ["nitrosamine", "nitrosamines"],
    "gmp": ["gmp", "good manufacturing practice"],
}

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

OUTCOME_PHRASES = {
    "failed": ["no significant", "no measurable", "inactive", "excluded", "not pursued"],
    "improved": ["improved", "increased", "enhanced", "more stable", "longer half-life"],
    "successful": ["significant", "potent", "strong activity"],
    "weak": ["weak", "limited"],
    "moderate": ["moderate"],
}

def detect_method_tags(sentence_l: str) -> list[str]:
    tags = []
    for tag, phrases in METHOD_TAGS.items():
        if any(p in sentence_l for p in phrases):
            tags.append(tag)
    return tags

def detect_failure_reason(sentence_l: str) -> str:
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

def detect_decision(sentence_l: str) -> tuple[str, str | None]:
    for decision, phrases in DECISION_PHRASES.items():
        if any(p in sentence_l for p in phrases):
            return decision, None
    return "unknown", None

def detect_outcome(sentence_l: str) -> str:
    for outcome in ["failed", "improved", "successful", "moderate", "weak"]:
        if any(p in sentence_l for p in OUTCOME_PHRASES[outcome]):
            return outcome
    return "unknown"

def classify_event_type(sentence_l: str, method_tags: list[str], failure_reason: str, decision_taken: str) -> str:
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
    if any(k in sentence_l for k in ["we conclude", "demonstrate", "significant", "robust", "strong"]):
        return "strong"
    if any(k in sentence_l for k in ["suggest", "may", "might", "could", "trend"]):
        return "weak"
    return "moderate"

def confidence_score_phase1(has_entity: bool, method_tags: list[str], failure_reason: str, decision_taken: str, has_measurements: bool, sentence_l: str = "") -> str:
    """
    PHASE 1: Improved confidence scoring
    Uses multi-signal detection to achieve better distribution
    """
    score = 0
    
    # Base signals
    if has_entity:
        score += 2
    if method_tags:
        score += 1
    if failure_reason != "unknown":
        score += 2
    if decision_taken != "unknown":
        score += 1
    if has_measurements:
        score += 2
    
    # Multi-signal boost
    high_signal_terms = [
        'lc-ms', 'mass spectrometry', 'in vivo', 'in vitro', 'clinical',
        'sequence', 'residues', 'ic50', 'ec50', 'half-life',
        'degraded', 'stable', 'potent', 'toxic', 'efficacy',
        'optimized', 'modified', 'abandoned', 'continued'
    ]
    
    signal_count = sum(1 for term in high_signal_terms if term in sentence_l)
    
    if signal_count >= 3:
        score += 2
    elif signal_count >= 2:
        score += 1
    
    return "high" if score >= 6 else "med" if score >= 3 else "low"

def suggested_keep(conf: str, event_type: str, failure_reason: str, decision_taken: str, tags: list[str]) -> int:
    if conf in ("med", "high"):
        return 1
    if event_type not in ("other",) and (failure_reason != "unknown" or decision_taken != "unknown" or tags):
        return 1
    return 0

# ---------------------------------------------------------
# DB inserts
# ---------------------------------------------------------
def upsert_source(con, source_id: str, pdf_file: str, metadata: dict):
    con.execute(
        """INSERT OR IGNORE INTO sources(source_id, pdf_file, title, authors, year, doi, imported_at)
           VALUES (?,?,?,?,?,?,?)""",
        (source_id, pdf_file, metadata.get('title'), metadata.get('authors'), 
         metadata.get('year'), metadata.get('doi'), now_iso()),
    )

def insert_document(con, source_id: str, file_path: str, sha256: str) -> str:
    doc_id = sha16(f"{source_id}|{file_path}|{sha256}")
    con.execute(
        """INSERT OR IGNORE INTO documents(doc_id, source_id, file_path, file_type, sha256, created_at)
           VALUES (?,?,?,?,?,?)""",
        (doc_id, source_id, file_path, "pdf", sha256, now_iso()),
    )
    return doc_id

def insert_chunk(con, source_id: str, doc_id: str, page_number: int, section_guess: str, chunk_text: str) -> str:
    chunk_id = sha16(f"{doc_id}|{page_number}|{chunk_text[:200]}")
    con.execute(
        """INSERT OR IGNORE INTO chunks(chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, now_iso()),
    )
    return chunk_id

def upsert_tag(con, tag: str):
    con.execute("INSERT OR IGNORE INTO tags(tag) VALUES(?)", (tag,))

def upsert_entity(con, entity_type: str, entity_name: str, entity_variant: str | None, organism: str | None) -> str:
    key = f"{entity_type}|{entity_name}|{entity_variant or ''}|{organism or ''}"
    entity_id = sha16(key)
    con.execute(
        """INSERT OR IGNORE INTO entities(entity_id, entity_type, entity_name, entity_variant, organism, created_at)
           VALUES (?,?,?,?,?,?)""",
        (entity_id, entity_type, entity_name, entity_variant, organism, now_iso()),
    )
    return entity_id

def insert_event(con, source_id: str, doc_id: str, chunk_id: str, page_number: int,
                 domain: str, event_type: str, study_stage: str, biological_system: str | None, application_area: str | None,
                 outcome: str, failure_reason: str, decision_taken: str, decision_driver: str | None,
                 evidence_snippet: str, evidence_strength_v: str, confidence_v: str) -> str:
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
            source_id, doc_id, chunk_id, page_number, now_iso()
        ),
    )
    return event_id

def link_event_entity(con, event_id: str, entity_id: str, role: str):
    con.execute(
        """INSERT OR IGNORE INTO event_entities(event_id, entity_id, role)
           VALUES (?,?,?)""",
        (event_id, entity_id, role),
    )

def link_event_tag(con, event_id: str, tag: str):
    upsert_tag(con, tag)
    con.execute(
        """INSERT OR IGNORE INTO event_tags(event_id, tag)
           VALUES (?,?)""",
        (event_id, tag),
    )

def insert_measurement(con, event_id: str, measurement: dict):
    measurement_id = sha16(f"{event_id}|{measurement['measurement_type']}|{measurement['value']}|{measurement['unit']}")
    con.execute(
        """INSERT OR IGNORE INTO quantitative_measurements(
             measurement_id, event_id, measurement_type, value, unit, context, created_at
           ) VALUES (?,?,?,?,?,?,?)""",
        (measurement_id, event_id, measurement['measurement_type'], 
         measurement['value'], measurement['unit'], measurement['context'], now_iso()),
    )

def normalize_event_key(event_type: str, entities: list, page: int, snippet: str) -> str:
    entity_str = "|".join(sorted(e['entity_name'] for e in entities))
    snippet_hash = sha16(snippet[:100])
    return f"{event_type}|{entity_str}|{page}|{snippet_hash}"

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Scrape PDFs for research intelligence - Phase 1 Enhanced')
    parser.add_argument('--domain', default='peptide', 
                       help='Research domain (peptide, stem_cell, oncology, etc.)')
    parser.add_argument('--input-dir', type=Path, default=Path('input_pdfs'),
                       help='Directory containing PDF files')
    parser.add_argument('--output-db', type=Path, default=Path('output/peptide_intel.sqlite'),
                       help='Output SQLite database path')
    args = parser.parse_args()
    
    global RESEARCH_DOMAIN, INPUT_DIR, DB_PATH
    RESEARCH_DOMAIN = args.domain
    INPUT_DIR = args.input_dir
    DB_PATH = args.output_db
    
    if not INPUT_DIR.exists():
        raise SystemExit(f"Missing folder: {INPUT_DIR.resolve()}")

    pdfs = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {INPUT_DIR.resolve()}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    con = sqlite3.connect(DB_PATH)
    try:
        inserted_events = 0
        total_measurements = 0
        failed_pdfs = []
        
        # Track entity coverage stats
        events_with_entities = 0
        total_entities_extracted = 0

        for pdf_path in tqdm(pdfs, desc="PDFs"):
            try:
                source_id = sha16(f"{pdf_path.name}|{pdf_path.stat().st_size}|{int(pdf_path.stat().st_mtime)}")
                file_hash = sha64(f"{pdf_path.name}|{pdf_path.stat().st_size}|{int(pdf_path.stat().st_mtime)}")

                with pdfplumber.open(str(pdf_path)) as pdf:
                    metadata = extract_metadata(pdf_path, pdf)
                    upsert_source(con, source_id, pdf_path.name, metadata)
                    doc_id = insert_document(con, source_id, str(pdf_path.resolve()), file_hash)

                    seen_events = set()

                    for page_idx, page in enumerate(pdf.pages, start=1):
                        try:
                            text = page.extract_text() or ""
                            if not text.strip():
                                continue

                            section = guess_section(text.lower())
                            chunk_id = insert_chunk(con, source_id, doc_id, page_idx, section, text)

                            for sent in chunk_sentences(text):
                                s_l = sent.lower()

                                has_signal = (
                                    any(p in s_l for lst in FAILURE_PHRASES.values() for p in lst) or
                                    any(p in s_l for lst in DECISION_PHRASES.values() for p in lst) or
                                    any(p in s_l for lst in METHOD_TAGS.values() for p in lst)
                                )
                                if not has_signal:
                                    continue

                                tags = detect_method_tags(s_l)
                                failure_reason = detect_failure_reason(s_l)
                                decision_taken, decision_driver = detect_decision(s_l)
                                outcome = detect_outcome(s_l)
                                stage = guess_stage(s_l)
                                event_type = classify_event_type(s_l, tags, failure_reason, decision_taken)
                                strength = evidence_strength(s_l)

                                # PHASE 1: Use enhanced entity extraction
                                ents = extract_all_entities(sent, metadata.get('title', ''))
                                measurements = extract_quantitative_data(sent)
                                
                                # Track entity coverage
                                if ents:
                                    events_with_entities += 1
                                    total_entities_extracted += len(ents)
                                
                                conf = confidence_score_phase1(bool(ents), tags, failure_reason, decision_taken, bool(measurements), s_l)
                                keep = suggested_keep(conf, event_type, failure_reason, decision_taken, tags)

                                if keep == 0 and event_type == "other":
                                    continue

                                event_key = normalize_event_key(event_type, ents, page_idx, sent)
                                if event_key in seen_events:
                                    continue
                                seen_events.add(event_key)

                                bio_sys = None
                                if "serum" in tags:
                                    bio_sys = "serum/plasma"
                                elif "organoid" in s_l:
                                    bio_sys = "organoid"
                                elif "cell line" in s_l or "cells" in s_l:
                                    bio_sys = "cells"

                                event_id = insert_event(
                                    con=con,
                                    source_id=source_id,
                                    doc_id=doc_id,
                                    chunk_id=chunk_id,
                                    page_number=page_idx,
                                    domain=RESEARCH_DOMAIN,
                                    event_type=event_type,
                                    study_stage=stage,
                                    biological_system=bio_sys,
                                    application_area=None,
                                    outcome=outcome,
                                    failure_reason=failure_reason,
                                    decision_taken=decision_taken,
                                    decision_driver=decision_driver,
                                    evidence_snippet=sent,
                                    evidence_strength_v=strength,
                                    confidence_v=conf,
                                )

                                for t in tags:
                                    link_event_tag(con, event_id, t)

                                for e in ents:
                                    entity_id = upsert_entity(con, e["entity_type"], e["entity_name"], e["entity_variant"], None)
                                    link_event_entity(con, event_id, entity_id, e.get("role", "unknown"))

                                for m in measurements:
                                    insert_measurement(con, event_id, m)
                                    total_measurements += 1

                                inserted_events += 1

                        except Exception as e:
                            print(f"  ⚠️  Error processing page {page_idx} of {pdf_path.name}: {e}")
                            continue

                con.commit()

            except Exception as e:
                print(f"❌ Error processing {pdf_path.name}: {e}")
                failed_pdfs.append(pdf_path.name)
                continue

        # Calculate entity coverage
        entity_coverage = (events_with_entities / inserted_events * 100) if inserted_events > 0 else 0
        avg_entities_per_event = (total_entities_extracted / inserted_events) if inserted_events > 0 else 0

        print(f"\n✅ Done!")
        print(f"   Inserted: ~{inserted_events} research events")
        print(f"   Measurements: {total_measurements}")
        print(f"   DB: {DB_PATH.resolve()}")
        print(f"\n📊 PHASE 1 Entity Coverage:")
        print(f"   Events with entities: {events_with_entities}/{inserted_events} ({entity_coverage:.1f}%)")
        print(f"   Total entities extracted: {total_entities_extracted}")
        print(f"   Avg entities per event: {avg_entities_per_event:.1f}")
        print(f"   Target: ≥70% coverage")
        
        if failed_pdfs:
            print(f"\n⚠️  Failed to process {len(failed_pdfs)} PDFs:")
            for pdf in failed_pdfs:
                print(f"   - {pdf}")
        
        print("\nNext step: Run export_csv_v2.py to export data for analysis.")
        
    finally:
        con.close()

if __name__ == "__main__":
    main()
