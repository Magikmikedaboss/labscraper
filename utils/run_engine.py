# (moved to end of file)
# Add at the very end of the file:
import re
import hashlib
import sqlite3
import argparse
import functools
from pathlib import Path
from datetime import datetime, timezone
import pdfplumber
from tqdm import tqdm
import logging

from pathlib import Path

# Define SEEDS_DIR to fix undefined variable error
if (Path('input/seeds').exists()):
    SEEDS_DIR = Path('input/seeds')
else:
    SEEDS_DIR = Path('seeds')

# Confidence scoring thresholds for evidence strength
HIGH_CONF_THRESHOLD = 6  # High confidence: strong evidence, multiple signals
MED_CONF_THRESHOLD = 3   # Medium confidence: moderate evidence

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
    # simple sentence split; good enough for v1
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
    # extremely light heuristics
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
    
    # Try PDF metadata first
    if pdf.metadata:
        metadata['title'] = pdf.metadata.get('Title')
        metadata['authors'] = pdf.metadata.get('Author')
        
        # Try to extract year from creation date
        if pdf.metadata.get('CreationDate'):
            try:
                year_match = re.search(r'(19|20)\d{2}', str(pdf.metadata.get('CreationDate')))
                if year_match:
                    metadata['year'] = int(year_match.group(0))
            except Exception as e:
                logging.exception(f"Error extracting year from CreationDate: {e}")
    
    # Try first page text for DOI and other metadata
    if pdf.pages:
        try:
            first_page = pdf.pages[0].extract_text() or ""
            
            # Extract DOI
            doi_match = re.search(r'doi[:\s]*(10\.\d{4,}/[^\s]+)', first_page, re.I)
            if doi_match:
                metadata['doi'] = doi_match.group(1).rstrip('.,;')
            
            # Extract year from text if not found in metadata
            if not metadata['year']:
                year_match = re.search(r'\b(19|20)\d{2}\b', first_page)
                if year_match:
                    metadata['year'] = int(year_match.group(0))
            
            # Try to extract title from first page if not in metadata
            if not metadata['title']:
                # Usually the title is in the first few lines
                lines = first_page.split('\n')[:10]
                for line in lines:
                    if len(line) > 20 and len(line) < 200:  # Reasonable title length
                        metadata['title'] = line.strip()
                        break
        except Exception as e:
            print(f"  ⚠️  Could not extract metadata from first page: {e}")
    
    return metadata

# ---------------------------------------------------------
# Entity extraction (universal)
# ---------------------------------------------------------
# Peptide regex - UPPERCASE ONLY, 8-100 AA
PEPTIDE_RE = re.compile(r"\b[ACDEFGHIKLMNPQRSTVWY]{8,100}\b")

# Sequence presentation patterns - stricter than before
# Only match patterns that are explicitly labeled as sequences
# Each pattern MUST have exactly ONE capture group for the sequence
# Use uppercase in patterns, we'll convert sentence to uppercase before matching
SEQUENCE_PRESENTATION_PATTERNS = [
    # Explicit sequence labeling only; avoid free-form OCR noise from figure legends.
    r'(?:SEQUENCE|SEQ(?:UENCE)?|PEPTIDE)(?:\s+ID(?:\s+NO\.?)?)?[\s:=-]+([ACDEFGHIKLMNPQRSTVWY]{8,100})\b',
    r'(?:SEQUENCE\s+WAS|SEQ(?:UENCE)?\s+WAS|PEPTIDE\s+WAS)\s+([ACDEFGHIKLMNPQRSTVWY]{8,100})\b',
    r'RESIDUES?\s+\d+[-–]\d+[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
    r'(?:N-TERMINUS|C-TERMINUS)[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
    r'(?:SEQUENCE|SEQ(?:UENCE)?|PEPTIDE)[^\n\r]{0,24}\(([ACDEFGHIKLMNPQRSTVWY]{8,100})\)',
    r'(?:SEQUENCE|SEQ(?:UENCE)?|PEPTIDE)[^\n\r]{0,24}\[([ACDEFGHIKLMNPQRSTVWY]{8,100})\]',
]

# Small stoplist for obvious non-peptides
FAKE_SEQUENCE_STOPLIST = {
    # Technical terms
    "MALDI", "FTICR", "HPLC", "LCMS", "LCMSMS", "MSMS",
    "UVVIS", "SDS", "PAGE", "NMR", "ELISA", "DNA", "RNA", "PCR",
    "HILIC", "UHPLC", "GCMS", "FACS", "FITC", "DAPI", "GFP",
    # Common words that slip through
    "PEPTIDE", "PEPTIDES", "SEQUENCE", "SEQUENCES", "RESIDUES",
    "CLINICAL", "TERMINAL", "MATERIALS", "RESEARCH", "ANALYSIS",
    "PATTERNS", "PATTERN", "FORMATS", "PRESENTS", "REPORTS",
    # Additional false positives found in testing / OCR-heavy figure legends
    "DEGRADATI", "DEGRADATION", "SYNTHESIS", "HARMLESS", "AMPHIPHILES",
    "AFFINITY", "REMAINING", "INCREASED", "ANDVICEVERSA", "INITIALLY",
    "ALDEHYDES", "CHEMISTS", "CLEAVAGE", "SEGMENTS", "LEFTPANELS",
    "SAMPLEHEATING", "ANDRISINGFAST", "IDENTITY", "DERIVATIVES", "AIRYSCAN",
    "MEDSCAPE", "INTERNET", "PIPELINE", "PERKINELMER", "GEHEALTHCARE",
}

# Known therapeutic peptides (whitelist)
KNOWN_PEPTIDES = {
    "ETELCALCETIDE", "PLECANATIDE", "TERIPARATIDE", "KYNETWRSED",
    "OCTREOTIDE", "LANREOTIDE", "PASIREOTIDE", "SOMATOSTATIN",
}

# ---------------------------------------------------------
# Seed File Loading
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
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                seeds.add(line.lower())
    
    return seeds


def get_seeds():
    compound = load_seed_file(SEEDS_DIR / "base/life_sciences/compounds.txt")
    target = load_seed_file(SEEDS_DIR / "base/life_sciences/targets.txt")
    model = load_seed_file(SEEDS_DIR / "base/life_sciences/models.txt")
    stopword = load_seed_file(SEEDS_DIR / "stopwords.txt")
    print("📋 Loaded seeds:")
    print(f"   Compounds: {len(compound)}")
    print(f"   Targets: {len(target)}")
    print(f"   Models: {len(model)}")
    print(f"   Stopwords: {len(stopword)}")
    return compound, target, model, stopword

TARGET_CONTEXT_WORDS = [
    "agonist", "antagonist", "inhibitor", "activator",
    "binding", "affinity", "receptor", "pathway", "signaling",
    "target", "modulator", "blocker",
]

def is_split_word(seq: str, sentence: str) -> bool:
    """Check if sequence looks like it was chopped from a larger English word"""
    # Find the sequence in the sentence (use uppercase for consistency)
    seq_upper = seq.upper()
    sentence_upper = sentence.upper()
    idx = sentence_upper.find(seq_upper)

    # If not found, check in whitespace-collapsed version (for OCR splits)
    if idx == -1:
        collapsed = sentence_upper.replace(" ", "")
        idx = collapsed.find(seq_upper)
        if idx == -1:
            return False
        # If found in collapsed, treat as split word
        return True

    # Check characters immediately before and after (use uppercase sentence)
    before_idx = idx - 1
    after_idx = idx + len(seq_upper)

    # If there's an alphabetic character immediately adjacent (and not a space), it's likely a split word
    # Allow for spaces and common punctuation between words
    if before_idx >= 0:
        before_char = sentence_upper[before_idx]
        if before_char.isalpha():
            return True
    if after_idx < len(sentence_upper):
        after_char = sentence_upper[after_idx]
        if after_char.isalpha():
            return True

    return False

def extract_presented_sequences(sentence: str) -> list[str]:
    """Extract sequences that are explicitly presented in the sentence"""
    sequences = []
    sentence_upper = sentence.upper()  # For matching uppercase sequences
    
    # Try each presentation pattern - use uppercase for matching
    for pattern in SEQUENCE_PRESENTATION_PATTERNS:
        matches = re.finditer(pattern, sentence_upper)
        for match in matches:
            seq = match.group(1)
            # Double-check it's valid AA sequence (only ACDEFGHIKLMNPQRSTVWY)
            if all(c in 'ACDEFGHIKLMNPQRSTVWY' for c in seq):
                # Filter out false positives using stoplist and validation
                if is_probable_peptide(seq, sentence):
                    sequences.append(seq)
    
    return list(set(sequences))

def is_probable_peptide(seq: str, sentence: str = "") -> bool:
    """Light validation with explicit-context safeguards against OCR word noise."""
    s = seq.upper().strip()
    
    # Whitelist: Known therapeutic peptides always pass
    if s in KNOWN_PEPTIDES:
        return True
    
    # Check stoplist
    if s in FAKE_SEQUENCE_STOPLIST:
        return False
    
    # Length check: 8-100 AA
    if len(s) < 8 or len(s) > 100:
        return False
    
    # At least 2 different amino acids (relaxed for common repeats like GGGGS)
    if len(set(s)) < 2:
        return False
    
    # Reject split words (chopped from larger English words)
    if sentence and is_split_word(s, sentence):
        return False

    if sentence:
        sentence_l = sentence.lower()
        has_sequence_context = any(
            hint in sentence_l for hint in [
                "sequence", "seq", "peptide", "residues", "n-terminus",
                "c-terminus", "amino acid", "amino-acid", "seq id"
            ]
        )
        appears_explicitly_uppercase = s in sentence

        # Fresh runs should only keep unlabeled sequences when authors explicitly present them in uppercase.
        if not has_sequence_context and not appears_explicitly_uppercase:
            return False
    
    return True

# Stem cell / general bio entities (super lightweight v1)
STEM_CELL_KEYWORDS = [
    "msc", "mesenchymal", "ipsc", "pluripotent", "stem cell", "stem-cell",
    "organoid", "differentiation", "reprogramming"
]


# ---------------------------------------------------------
# Lazy-loaded seed files
# ---------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _get_compound_seeds():
    return load_seed_file(SEEDS_DIR / "base/life_sciences/compounds.txt")

@functools.lru_cache(maxsize=1)
def _get_target_seeds():
    return load_seed_file(SEEDS_DIR / "base/life_sciences/targets.txt")

@functools.lru_cache(maxsize=1)
def _get_model_seeds():
    return load_seed_file(SEEDS_DIR / "base/life_sciences/models.txt")

@functools.lru_cache(maxsize=1)
def _get_stopword_seeds():
    return load_seed_file(SEEDS_DIR / "stopwords.txt")

def extract_compounds(sentence: str) -> list[dict]:
    """Extract compound/drug names from sentence"""
    compounds = []
    s_l = sentence.lower()
    extracted_names = set()
    # Check seed list
    for compound in _get_compound_seeds():
        if re.search(r'\b' + re.escape(compound) + r'\b', s_l):
            name = compound.upper()
            if name not in extracted_names:
                compounds.append({
                    "entity_type": "compound",
                    "entity_name": name,
                    "entity_variant": "drug",
                    "role": "tested",
                    "text": sentence
                })
                extracted_names.add(name)
    return compounds

def extract_targets(sentence: str) -> list[dict]:
    """Extract biological targets - NO context gate, case-insensitive matching"""
    targets = []
    
    # Check seed list with case-insensitive matching
    for target in _get_target_seeds():
        # Match case-insensitively (handles MTOR, mTOR, mtor, etc.)
        if re.search(r'\b' + re.escape(target) + r'\b', sentence, re.IGNORECASE):
            targets.append({
                "entity_type": "target",
                "entity_name": target.upper(),
                "entity_variant": "protein",
                "role": "target",
                "text": sentence
            })
    
    return targets

def extract_models(sentence: str) -> list[dict]:
    """Extract experimental models from unified seed list"""
    models = []
    s_l = sentence.lower()
    for model in _get_model_seeds():
        if re.search(r'\b' + re.escape(model) + r'\b', s_l):
            variant = "unknown"
            role = "model"
            if any(char.isdigit() for char in model) or '-' in model:
                variant = "cell_line"
                role = "model"
            elif model in ["mouse", "mice", "rat", "rats", "human", "humans", "rabbit", "guinea pig", \
                          "hamster", "zebrafish", "drosophila", "c. elegans", "xenopus", "primate", \
                          "pig", "dog"]:
                variant = "organism"
                role = "model"
            elif model in ["serum", "plasma", "blood", "csf", "cerebrospinal fluid", "urine", \
                          "saliva", "synovial fluid", "peritoneal fluid", "ascites"]:
                variant = "biofluid"
                role = "matrix"
            elif model in ["liver", "kidney", "heart", "brain", "lung", "spleen", "muscle", \
                          "adipose", "pancreas", "intestine", "colon", "stomach", "skin", "bone", "cartilage"]:
                variant = "tissue"
                role = "model"
            elif "organoid" in model or "spheroid" in model or "3d" in model:
                variant = "3d_model"
                role = "model"
            models.append({
                "entity_type": "model",
                "entity_name": model.upper() if model.isupper() or len(model) <= 5 else model.capitalize(),
                "entity_variant": variant,
                "role": role,
                "text": sentence
            })
    return models

def extract_entities(sentence: str, domain: str = "methods_tooling") -> list[dict]:
    """
    Extract all entity types based on domain
    - construction_science: material, system, environment, failure_mode, hazard, test_method
    - methods_tooling: compound, peptide, target, model, stem_cell (biomedical)
    
    Returns: list of {entity_type, entity_name, entity_variant, role}
    """
    ents = []
    
    # Track extracted names to avoid duplicates
    extracted_names = set()
    
    # Domain-specific entity extraction
    if domain == "construction_science":
        # Construction science entities ONLY
        ents.extend(extract_construction_entities(sentence, extracted_names))
    else:
        # Default to biomedical entities for other domains
        ents.extend(extract_biomedical_entities(sentence, extracted_names))
    
    return ents

def extract_construction_entities(sentence: str, extracted_names: set) -> list[dict]:
    """Extract construction science entities"""
    ents = []
    s_l = sentence.lower()
    
    # Construction materials
    construction_materials = {
        "concrete", "steel", "wood", "timber", "brick", "stone", "glass", "plastic",
        "aluminum", "copper", "iron", "composite", "polymer", "ceramic", "asphalt"
    }
    
    # Construction systems
    construction_systems = {
        "foundation", "wall", "roof", "floor", "beam", "column", "truss", "frame",
        "slab", "panel", "cladding", "insulation", "ventilation", "plumbing", "electrical"
    }
    
    # Environmental exposures
    environmental_exposures = {
        "temperature", "humidity", "moisture", "rain", "snow", "wind", "sunlight",
        "UV", "freeze", "thaw", "corrosion", "rust", "mold", "mildew", "fungi"
    }
    
    # Failure modes
    failure_modes = {
        "crack", "cracking", "fracture", "break", "failure", "collapse", "buckling",
        "deflection", "deformation", "creep", "fatigue", "deterioration", "degradation"
    }
    
    # Hazards
    hazards = {
        "fire", "earthquake", "flood", "wind", "seismic", "impact", "blast", "explosion"
    }
    
    # Test methods
    test_methods = {
        "compression", "tension", "bending", "shear", "torsion", "impact", "fatigue",
        "corrosion", "weathering", "thermal", "fire", "seismic", "load", "stress", "strain"
    }
    
    # Extract materials
    for material in construction_materials:
        if re.search(r'\b' + re.escape(material) + r'\b', s_l):
            name = material.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "material",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "material"
                })
                extracted_names.add(name)
    
    # Extract systems
    for system in construction_systems:
        if re.search(r'\b' + re.escape(system) + r'\b', s_l):
            name = system.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "system",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "system"
                })
                extracted_names.add(name)
    
    # Extract environmental exposures
    for env in environmental_exposures:
        if re.search(r'\b' + re.escape(env) + r'\b', s_l):
            name = env.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "environment",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "exposure"
                })
                extracted_names.add(name)
    
    # Extract failure modes
    for failure in failure_modes:
        if re.search(r'\b' + re.escape(failure) + r'\b', s_l):
            name = failure.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "failure_mode",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "failure"
                })
                extracted_names.add(name)
    
    # Extract hazards
    for hazard in hazards:
        if re.search(r'\b' + re.escape(hazard) + r'\b', s_l):
            name = hazard.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "hazard",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "hazard"
                })
                extracted_names.add(name)
    
    # Extract test methods
    for test in test_methods:
        if re.search(r'\b' + re.escape(test) + r'\b', s_l):
            name = test.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "test_method",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "test"
                })
                extracted_names.add(name)
    
    return ents

def extract_biomedical_entities(sentence: str, extracted_names: set) -> list[dict]:
    """Extract biomedical entities (original logic)"""
    ents = []
    s_l = sentence.lower()
    
    # 1) COMPOUND FIRST: Drug/molecule names (PRIORITY)
    for compound in _get_compound_seeds():
        if re.search(r'\b' + re.escape(compound) + r'\b', s_l):
            name = compound.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "compound",
                    "entity_name": name,
                    "entity_variant": "drug",
                    "role": "tested",
                    "text": sentence
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
                "role": "tested",
                "text": sentence
            })
            extracted_names.add(seq)

    # 3) TARGET: Biological targets
    for target in _get_target_seeds():
        if re.search(r'\b' + re.escape(target) + r'\b', sentence, re.IGNORECASE):
            name = target.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "target",
                    "entity_name": name,
                    "entity_variant": "protein",
                    "role": "target",
                    "text": sentence
                })
                extracted_names.add(name)
    
    # 4) MODEL: Experimental systems
    for e in extract_models(sentence):
        # Promote neural cell types to 'neural_cell' if present in the name
        name_lower = e["entity_name"].lower()
        if any(neural in name_lower for neural in ["neuron", "neurons", "microglia", "astrocyte", "astrocytes"]):
            e["entity_type"] = "neural_cell"
        if e["entity_name"] not in extracted_names:
            e["text"] = sentence
            ents.append(e)
            extracted_names.add(e["entity_name"])
    
    # 5) STEM_CELL: Stem cell keywords
    for k in STEM_CELL_KEYWORDS:
        if k in s_l:
            name = k.upper() if k in ["msc", "ipsc"] else k
            if name not in extracted_names:
                ents.append({
                    "entity_type": "stem_cell",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "tested",
                    "text": sentence
                })
                extracted_names.add(name)

    # Type precedence rules
    neural_cell_names = {"microglia", "astrocyte", "neuron", "neurons"}
    model_names = {"organoid", "organoids"}
    stem_cell_names = {"ipsc", "msc", "esc"}

    for e in ents:
        name_lower = e["entity_name"].lower()
        if name_lower in neural_cell_names:
            e["entity_type"] = "neural_cell"
        elif name_lower in model_names:
            e["entity_type"] = "model"
        elif name_lower in stem_cell_names:
            e["entity_type"] = "stem_cell"

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
# Entity Relationship Detection
# ---------------------------------------------------------
RELATIONSHIP_PATTERNS = [
    (r'(\w+)\s+(?:was|is|showed)\s+more\s+stable\s+than\s+(\w+)', 'more_stable_than'),
    (r'(\w+)\s+(?:was|is|showed)\s+more\s+potent\s+than\s+(\w+)', 'more_potent_than'),
    (r'(\w+)\s+(?:was|is)\s+less\s+toxic\s+than\s+(\w+)', 'less_toxic_than'),
    (r'(\w+)\s+(?:is|was)\s+(?:a|an)\s+analog\s+of\s+(\w+)', 'analog_of'),
    (r'(\w+)\s+(?:is|was)\s+(?:a|an)\s+derivative\s+of\s+(\w+)', 'derivative_of'),
]

def extract_relationships(sentence: str, entities: list[dict]) -> list[dict]:
    """Extract relationships between entities"""
    relationships = []
    s_l = sentence.lower()
    
    # Create entity name set for validation
    entity_names = {e['entity_name'].lower() for e in entities}
    
    for pattern, rel_type in RELATIONSHIP_PATTERNS:
        matches = re.finditer(pattern, s_l)
        for m in matches:
            entity1 = m.group(1).upper()
            entity2 = m.group(2).upper()
            
            # Only add if both entities are in our extracted entities
            if entity1.lower() in entity_names and entity2.lower() in entity_names:
                relationships.append({
                    'entity_1': entity1,
                    'entity_2': entity2,
                    'relationship_type': rel_type,
                    'confidence': 'med'
                })
    
    return relationships

# ---------------------------------------------------------
# Event classification rules (universal)
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
    "abandoned": ["not pursued", "not pursued further", "excluded", "discarded", "abandoned", "dropped"],
    "modified": ["optimized", "modified", "analog", "derivative", "cyclized", "pegylated", "amidated", "redesigned"],
    "continued": ["further study", "continued", "follow-up", "subsequently", "next we", "we decided", "decided to", "chose to"],
    "paused": ["inconclusive", "unclear", "requires further investigation", "pending"],
    "replicated": ["replicated", "repeated", "validated", "confirmed"],
    "escalated": ["advanced to", "moved to", "in vivo", "clinical", "progressed to"],
}

OUTCOME_PHRASES = {
    # Prioritize negative evidence first to avoid false positives from words like "improved"
    # inside phrases such as "no significant improvement".
    "negative": [
        "no significant", "no measurable", "inactive", "excluded", "not pursued", "did not",
        "failed to", "no improvement", "worsened", "decreased", "declined", "degradation",
        "toxic", "toxicity", "adverse"
    ],
    "positive": [
        "improved", "increased", "enhanced", "more stable", "longer half-life", "better",
        "higher", "greater", "successful", "showed activity", "demonstrated", "significant"
    ],
    "neutral": ["moderate", "marginal", "partial", "mixed", "limited", "trend"],
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
            # map some to canonical failure_reason values
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
            # decision_driver is guessed from nearby issues later
            return decision, None
    return "unknown", None

def detect_outcome(sentence_l: str) -> str:
    for outcome in ["negative", "positive", "neutral"]:
        if any(p in sentence_l for p in OUTCOME_PHRASES[outcome]):
            return outcome
    return "unknown"

def classify_event_type(sentence_l: str, method_tags: list[str], failure_reason: str, decision_taken: str) -> str:
    # Regulatory risk triggers
    if "nitrosamine" in method_tags or failure_reason == "regulatory":
        return "regulatory_risk"
    # Toxicity
    if failure_reason == "toxicity_flag":
        return "toxicity_flag"
    # Stability
    if failure_reason == "stability_failure":
        return "stability_issue"
    # Efficacy/Activity
    if failure_reason == "no_activity" or any(k in sentence_l for k in ["activity", "efficacy", "potent", "ic50", "ec50"]):
        return "efficacy_result"
    # Manufacturing/scalability
    if failure_reason == "scalability" or any(k in sentence_l for k in ["manufacturing", "scale-up", "yield"]):
        return "manufacturing_constraint"
    # Methods and tradeoffs
    if method_tags:
        if any(k in sentence_l for k in ["cost-intensive", "expensive", "time-consuming", "fast", "cost-effective"]):
            return "cost_tradeoff"
        return "method_evaluation"
    # Decision point
    if decision_taken != "unknown":
        return "decision_point"
    return "other"

def evidence_strength(sentence_l: str) -> str:
    # lightweight heuristic
    if any(k in sentence_l for k in ["we conclude", "demonstrate", "significant", "robust", "strong"]):
        return "strong"
    if any(k in sentence_l for k in ["suggest", "may", "might", "could", "trend"]):
        return "weak"
    return "moderate"

def confidence_score(has_entity: bool, method_tags: list[str], failure_reason: str, decision_taken: str, has_measurements: bool, sentence_l: str = "") -> str:
    """
    Compute a confidence label ("high", "med", "low") for an evidence sentence.
    
    Scoring rationale:
    - Entities, method tags, failure reason, decision taken, and measurements each contribute to the score.
    - High-signal terms in the sentence provide additional boosts.
    - Thresholds: HIGH_CONF_THRESHOLD = 6, MED_CONF_THRESHOLD = 3 (see module constants).
    - High: strong evidence (multiple signals); Med: moderate evidence; Low: weak or ambiguous evidence.
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
    
    # FIX C: Multi-signal boost
    # Count high-signal terms in sentence
    high_signal_terms = [
        'lc-ms', 'mass spectrometry', 'in vivo', 'in vitro', 'clinical',
        'sequence', 'residues', 'ic50', 'ec50', 'half-life',
        'degraded', 'stable', 'potent', 'toxic', 'efficacy',
        'optimized', 'modified', 'abandoned', 'continued'
    ]
    
    signal_count = sum(1 for term in high_signal_terms if term in sentence_l)
    
    # Boost confidence if multiple signals present
    if signal_count >= 3:
        score += 2  # Strong multi-signal boost
    elif signal_count >= 2:
        score += 1  # Moderate multi-signal boost
    
    # Use named constants for thresholds
    # Old: high>=6, med>=3 gave 0.3% high, 17% med, 83% low
    # New: high>=6, med>=3 with multi-signal boost
    if score >= HIGH_CONF_THRESHOLD:
        return "high"
    elif score >= MED_CONF_THRESHOLD:
        return "med"
    else:
        return "low"

def suggested_keep(conf: str, event_type: str, failure_reason: str, decision_taken: str, tags: list[str]) -> int:
    if conf in ("med", "high"):
        return 1
    if event_type not in ("other",) and (failure_reason != "unknown" or decision_taken != "unknown" or tags):
        return 1
    return 0

# ---------------------------------------------------------
# DB inserts (universal)
# ---------------------------------------------------------
def upsert_source(con, source_id: str, pdf_file: str, metadata: dict):
    """Updated to include metadata"""
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
    """Insert quantitative measurement"""
    measurement_id = sha16(f"{event_id}|{measurement['measurement_type']}|{measurement['value']}|{measurement['unit']}")
    con.execute(
        """INSERT OR IGNORE INTO quantitative_measurements(
             measurement_id, event_id, measurement_type, value, unit, context, created_at
           ) VALUES (?,?,?,?,?,?,?)""",
        (measurement_id, event_id, measurement['measurement_type'], 
         measurement['value'], measurement['unit'], measurement['context'], now_iso()),
    )

def insert_relationship(con, event_id: str, entity_id_1: str, entity_id_2: str, 
                       relationship_type: str, confidence: str):
    """Insert entity relationship"""
    relationship_id = sha16(f"{entity_id_1}|{entity_id_2}|{relationship_type}|{event_id}")
    con.execute(
        """INSERT OR IGNORE INTO entity_relationships(
             relationship_id, entity_id_1, entity_id_2, relationship_type, 
             event_id, confidence, created_at
           ) VALUES (?,?,?,?,?,?,?)""",
        (relationship_id, entity_id_1, entity_id_2, relationship_type, 
         event_id, confidence, now_iso()),
    )

# ---------------------------------------------------------
# Deduplication
# ---------------------------------------------------------
def normalize_event_key(event_type: str, entities: list, page: int, snippet: str) -> str:
    """Create key for deduplication"""
    entity_str = "|".join(sorted(e['entity_name'] for e in entities))
    snippet_hash = sha16(snippet[:100])
    return f"{event_type}|{entity_str}|{page}|{snippet_hash}"

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main(domain: str | None = None, input_dir: Path | None = None, db_path: Path | None = None, lenses: list | None = None):
    # Parse command line arguments only if all parameters are None
    parser = argparse.ArgumentParser(description='Scrape PDFs for research intelligence')
    parser.add_argument('--domain', default='methods_tooling', 
                       help='Research domain (methods_tooling, drug_discovery, etc.)')
    parser.add_argument('--input-dir', type=Path, default=Path('input/pdfs'),
                       help='Directory containing PDF files')
    parser.add_argument('--output-db', type=Path, default=Path('db/runs.sqlite'),
                       help='Output SQLite database path')

    if domain is None and input_dir is None and db_path is None:
        args = parser.parse_args()
        research_domain = args.domain
        input_dir = args.input_dir
        db_path = args.output_db
    else:
        research_domain = domain if domain is not None else 'methods_tooling'
        input_dir = input_dir if input_dir is not None else Path('input/pdfs')
        db_path = db_path if db_path is not None else Path('db/runs.sqlite')
    
    # TODO: Implement lens filtering when lens system is ready
    # Currently lenses parameter is accepted but not used
    if lenses is not None:
        print(f"⚠️  Lenses parameter provided but not implemented yet: {lenses}")
        # Future implementation would filter processing based on selected lenses
    
    if isinstance(input_dir, str):
        input_dir = Path(input_dir)
    if isinstance(db_path, str):
        db_path = Path(db_path)
    
    if not input_dir.exists():
        raise SystemExit(f"Missing folder: {input_dir.resolve()}")

    # Recursively find all PDFs in input_dir and subfolders
    pdfs = sorted(input_dir.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs to process in {input_dir.resolve()}")
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {input_dir.resolve()}")

    # Ensure output directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use context manager for database connection
    with sqlite3.connect(db_path) as con:
        # Schema initialization is handled by init_db.py; do not run migrations here
        # Initialize schema if tables don't exist
        con.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                pdf_file TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                year INTEGER,
                doi TEXT,
                imported_at TEXT NOT NULL
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sources (source_id)
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                section_guess TEXT,
                chunk_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id),
                FOREIGN KEY (source_id) REFERENCES sources (source_id)
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS research_events (
                event_id TEXT PRIMARY KEY,
                research_domain TEXT NOT NULL,
                event_type TEXT NOT NULL,
                study_stage TEXT,
                biological_system TEXT,
                application_area TEXT,
                outcome TEXT,
                failure_reason TEXT,
                decision_taken TEXT,
                decision_driver TEXT,
                evidence_snippet TEXT,
                evidence_strength TEXT,
                confidence TEXT,
                source_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sources (source_id),
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id),
                FOREIGN KEY (chunk_id) REFERENCES chunks (chunk_id)
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                entity_variant TEXT,
                organism TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS event_entities (
                event_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                role TEXT,
                PRIMARY KEY (event_id, entity_id),
                FOREIGN KEY (event_id) REFERENCES research_events (event_id),
                FOREIGN KEY (entity_id) REFERENCES entities (entity_id)
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS entity_relationships (
                relationship_id TEXT PRIMARY KEY,
                entity_id_1 TEXT NOT NULL,
                entity_id_2 TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                event_id TEXT,
                confidence TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entity_id_1) REFERENCES entities (entity_id),
                FOREIGN KEY (entity_id_2) REFERENCES entities (entity_id),
                FOREIGN KEY (event_id) REFERENCES research_events (event_id)
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                tag TEXT PRIMARY KEY
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS event_tags (
                event_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (event_id, tag),
                FOREIGN KEY (event_id) REFERENCES research_events (event_id),
                FOREIGN KEY (tag) REFERENCES tags (tag)
            )
        """)
        
        con.execute("""
            CREATE TABLE IF NOT EXISTS quantitative_measurements (
                measurement_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                measurement_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                context TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES research_events (event_id)
            )
        """)

        for pdf_path in tqdm(pdfs, desc="PDFs"):
            print(f"Processing PDF: {pdf_path}")
            try:
                # create stable-ish ids
                source_id = sha16(f"{pdf_path.name}|{pdf_path.stat().st_size}|{int(pdf_path.stat().st_mtime)}")
                file_hash = sha64(f"{pdf_path.name}|{pdf_path.stat().st_size}|{int(pdf_path.stat().st_mtime)}")

                with pdfplumber.open(str(pdf_path)) as pdf:
                    # Extract metadata
                    metadata = extract_metadata(pdf_path, pdf)
                    upsert_source(con, source_id, pdf_path.name, metadata)
                    doc_id = insert_document(con, source_id, str(pdf_path.resolve()), file_hash)



                    for page_idx, page in enumerate(pdf.pages, start=1):
                        try:
                            text = page.extract_text() or ""
                            if not text.strip():
                                continue
                            section = guess_section(text.lower())
                            chunk_id = insert_chunk(con, source_id, doc_id, page_idx, section, text)
                            # sentence scan
                            for sent in chunk_sentences(text):
                                s_l = sent.lower()
                                # keep only sentences with any signal
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
                                entities = extract_entities(sent, research_domain)
                                quantitative = extract_quantitative_data(sent)
                                # Compute confidence
                                conf = confidence_score(bool(entities), tags, failure_reason, decision_taken, bool(quantitative), s_l)
                                # Insert event
                                event_id = insert_event(
                                    con, source_id, doc_id, chunk_id, page_idx,
                                    research_domain, event_type, stage, None, None,
                                    outcome, failure_reason, decision_taken, decision_driver,
                                    sent, strength, conf
                                )
                                # Link entities
                                for ent in entities:
                                    entity_id = upsert_entity(
                                        con,
                                        ent.get("entity_type"),
                                        ent.get("entity_name"),
                                        ent.get("entity_variant"),
                                        ent.get("organism") if "organism" in ent else None
                                    )
                                    link_event_entity(con, event_id, entity_id, ent.get("role", ""))
                                # Link tags
                                for tag in tags:
                                    link_event_tag(con, event_id, tag)
                                # Insert quantitative measurements
                                for m in quantitative:
                                    insert_measurement(con, event_id, m)
                        except Exception as e:
                            print(f"  ⚠️  Error processing page {page_idx} in {pdf_path.name}: {e}")
            except Exception as e:
                print(f"  ⚠️  Error processing PDF {pdf_path.name}: {e}")



