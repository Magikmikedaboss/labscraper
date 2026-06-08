import regex as re
from utils.common import get_compound_seeds, get_target_seeds, get_model_seeds


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def normalize_name(name: str, preserve_spaces: bool = False) -> str:
    """Normalize entity text for deduplication or matching.

    When preserve_spaces is False, whitespace and punctuation are removed.
    When preserve_spaces is True, repeated whitespace is collapsed to single
    spaces and punctuation is preserved.
    """
    normalized = name.strip().lower()
    if preserve_spaces:
        return re.sub(r"\s+", " ", normalized)
    return re.sub(r"[\s\-_,.;:]+", "", normalized)


STEM_CELL_KEYWORDS = [
    "msc", "mesenchymal", "ipsc", "pluripotent",
    "stem cell", "stem-cell",
    # "organoid" REMOVED — typed as model via models.txt
    "differentiation", "reprogramming"
]

NEURAL_CELL_KEYWORDS = [
    "neuron",
    "neurons",
    "dopaminergic",
    "glutamatergic",
    "gabaergic",
    "astrocyte",
    "astrocytes",
    "oligodendrocyte",
    "oligodendrocytes",
    "microglia",
    "microglial",
]

PEPTIDE_DENYLIST = {
    "CANADIAN",
    "CLIMATE",
    "PREFACE",
    "PRINCIPAL",
    "SERVICE",
    "PACIFIC",
}

FALLBACK_MODELS = ["mouse", "rat", "human", "hela", "hek293"]

CONSTRUCTION_MATERIALS = {
    "concrete", "steel", "wood", "glass", "brick", "timber", "mortar", "insulation",
    "polymer", "composite", "asphalt", "aluminum", "copper", "gypsum", "plaster",
    "ceramic", "stone", "aggregate", "fiber", "foam", "bitumen", "pvc", "eps",
    "xps", "hdpe", "ldpe",
}

CONSTRUCTION_SYSTEMS = {
    "wall", "roof", "foundation", "floor", "column", "beam", "slab", "girder",
    "truss", "panel", "joint", "window", "door", "façade", "cladding",
    "insulation system", "partition", "rafter", "stud", "joist", "lintel",
}

CONSTRUCTION_FAILURE_MODES = {
    "crack", "cracking", "shear failure", "buckling", "fatigue", "delamination",
    "fracture", "rupture", "collapse", "spalling", "yielding", "debonding",
    "creep", "shrinkage", "corrosion fatigue", "brittle fracture", "ductile fracture",
    "plastic hinge", "instability", "microcrack", "macrocrack",
}

CONSTRUCTION_ENVIRONMENTS = {
    "temperature", "thermal cycling", "humidity", "moisture", "wind", "rain", "fire",
    "freeze", "frost", "uv", "solar", "environmental stress", "exposure",
    "condensation", "weather", "climate", "precipitation", "snow", "hail",
    "thermal shock",
}

CONSTRUCTION_TEST_METHODS = {
    "compression", "tension", "shear", "bending", "torsion", "impact", "flexure",
    "creep test", "fatigue test", "tensile test", "load test", "stress test",
    "thermal analysis", "modulus", "stiffness", "ductility", "hardness", "strength",
    "yield strength", "ultimate strength", "elasticity", "plasticity",
}

CONSTRUCTION_HAZARDS = {
    "flood", "seismic", "earthquake", "corrosion", "erosion", "vibration", "overload",
    "fire hazard", "chemical attack", "abrasion", "freeze-thaw", "alkali-silica reaction",
    "subsidence", "settlement", "liquefaction", "tsunami", "landslide", "storm",
    "hurricane", "typhoon", "cyclone",
}

CONSTRUCTION_ENTITY_GROUPS = [
    (CONSTRUCTION_MATERIALS, "material"),
    (CONSTRUCTION_SYSTEMS, "system"),
    (CONSTRUCTION_FAILURE_MODES, "failure_mode"),
    (CONSTRUCTION_ENVIRONMENTS, "environment"),
    (CONSTRUCTION_TEST_METHODS, "test_method"),
    (CONSTRUCTION_HAZARDS, "hazard"),
]

TARGET_CONTEXT_TERMS = (
    "protein",
    "gene",
    "receptor",
    "kinase",
    "phosphorylation",
    "expression",
    "signaling",
    "pathway",
    "assay",
    "cell",
    "cells",
    "compound",
    "treatment",
    "inhibitor",
    "inhibition",
    "mutation",
    "disease",
    "binding",
)


def _has_target_context(sentence: str) -> bool:
    sentence_l = sentence.lower()
    return any(term in sentence_l for term in TARGET_CONTEXT_TERMS)


# ---------------------------------------------------------
# COMPOUNDS
# ---------------------------------------------------------
def extract_compounds(sentence: str, SEEDS_DIR=None) -> list[dict]:
    compounds = []
    for compound in get_compound_seeds(SEEDS_DIR):
        if re.search(r'(?<![\p{L}\p{N}])' + re.escape(compound) + r'(?![\p{L}\p{N}])', sentence, re.IGNORECASE):
            compounds.append({
                "entity_type": "compound",
                "entity_name": compound.upper(),
                "entity_variant": "small_molecule",
                "role": "tested",
                "text": sentence,
            })
    return compounds


def extract_targets(sentence: str, SEEDS_DIR=None) -> list[dict]:
    targets = []
    has_target_context = _has_target_context(sentence)
    for target in get_target_seeds(SEEDS_DIR):
        if len(target) <= 3 and not has_target_context:
            continue
        if re.search(r'(?<![\p{L}\p{N}])' + re.escape(target) + r'(?![\p{L}\p{N}])', sentence, re.IGNORECASE):
            targets.append({
                "entity_type": "target",
                "entity_name": target.upper(),
                "entity_variant": "protein",
                "role": "target",
                "text": sentence,
            })
    return targets


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------
def extract_models(sentence: str, SEEDS_DIR=None) -> list[dict]:
    seen = set()
    models = []
    for model in get_model_seeds(SEEDS_DIR):
        if re.search(r'\b' + re.escape(model) + r'\b', sentence, re.IGNORECASE):
            variant = "unknown"
            if any(c.isdigit() for c in model) or '-' in model:
                variant = "cell_line"
            elif model.lower() in {"mouse", "mice", "rat", "human"}:
                variant = "organism"
            elif "organoid" in model.lower() or "3d" in model.lower():
                variant = "3d_model"
            name = model.upper()
            if name not in seen:
                models.append({
                    "entity_type": "model",
                    "entity_name": name,
                    "entity_variant": variant,
                    "text": sentence,
                })
                seen.add(name)

    for fm in FALLBACK_MODELS:
        if re.search(r'\b' + re.escape(fm) + r'\b', sentence, re.IGNORECASE):
            name = fm.upper()
            if name not in seen:
                variant = "cell_line" if fm in {"hela", "hek293"} else "organism"
                models.append({
                    "entity_type": "model",
                    "entity_name": name,
                    "entity_variant": variant,
                    "text": sentence,
                })
                seen.add(name)
    return models


# ---------------------------------------------------------
# SEQUENCES / PEPTIDES
# ---------------------------------------------------------
def extract_presented_sequences(sentence: str) -> list:
    # Only match canonical AA codes, min length 7, or uppercase tokens with SEQ ID context
    aa_pattern = r'\b[ACDEFGHIKLMNPQRSTVWY]{7,}\b'
    seqs = re.findall(aa_pattern, sentence)
    # Also allow uppercase tokens of length >=5 if they appear with (SEQ ID NO: n)
    seqid_matches = re.findall(r'([A-Z]{5,})\s*\(SEQ ID NO: \d+\)', sentence)
    seqs += [m for m in seqid_matches if m not in seqs]
    return seqs


def is_probable_peptide(seq: str, sentence: str) -> bool:
    aa_set = set("ACDEFGHIKLMNPQRSTVWY")
    seq = seq.strip().upper()
    if seq in PEPTIDE_DENYLIST:
        return False
    # Accept only if fullmatch of AA codes and length >=7
    if re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]{7,}', seq):
        return True
    # Otherwise, only allow fallback if SEQ ID context is present
    if "SEQ ID NO" in sentence.upper():
        if len(seq) < 5:
            return False
        valid = [c for c in seq if c in aa_set]
        frac_valid = len(valid) / len(seq) if seq else 0
        return frac_valid >= 0.8 and len(set(valid)) >= 3
    return False


# ---------------------------------------------------------
# MAIN ENTITY ROUTER
# ---------------------------------------------------------
def extract_entities(sentence: str, domain: str = "methods_tooling", SEEDS_DIR=None) -> list[dict]:
    extracted_names = set()
    if domain == "construction_science":
        return extract_construction_entities(sentence, extracted_names, SEEDS_DIR=SEEDS_DIR)
    return extract_biomedical_entities(sentence, extracted_names, SEEDS_DIR=SEEDS_DIR)


FAILURE_PATTERNS = (
    r"(shear|fatigue|stress|thermal|brittle|ductile|creep|shrinkage|corrosion) (failure|crack|fracture|collapse|spalling)",
    r"(failure|crack|fracture|collapse|spalling) (due to|from|by) (shear|fatigue|stress|thermal|creep|corrosion)",
    r"([a-z]+) (fracture|crack|failure|collapse)",
    r"(fracture|crack|failure|collapse) of ([a-z]+)",
)

COMPILED_FAILURE_REGEX = [re.compile(pattern) for pattern in FAILURE_PATTERNS]


def _find_specific_failure_phrases(sentence: str) -> list[str]:
    matches = []
    lowered_sentence = sentence.lower()
    for pattern in COMPILED_FAILURE_REGEX:
        for match in pattern.findall(lowered_sentence):
            if isinstance(match, tuple):
                matches.append(" ".join([word for word in match if word]))
            else:
                matches.append(match)
    return matches


# ---------------------------------------------------------
# CONSTRUCTION DOMAIN
def extract_construction_entities(sentence: str, extracted_names: set, SEEDS_DIR=None) -> list[dict]:
    ents = []
    s_l = sentence.lower()

    # Add specific failures first
    for specific in _find_specific_failure_phrases(sentence):
        name = specific.upper()
        norm = normalize_name(name)
        if norm not in extracted_names:
            ents.append({
                "entity_type": "failure_mode",
                "entity_name": name,
                "role": "failure_mode",
                "text": sentence
            })
            extracted_names.add(norm)

    # Add all other entities, allow partial matches and include generic terms if paired with descriptors
    generic_skip = {"failure", "thermal", "stress"}
    has_generic = any(re.search(r'\b' + re.escape(g) + r'\b', s_l) for g in generic_skip)
    has_failure_context = any(re.search(r'\b' + re.escape(x) + r'\b', s_l) for x in ["crack", "fracture", "collapse", "spalling"])
    for group, entity_type in CONSTRUCTION_ENTITY_GROUPS:
        for item in group:
            item_l = item.lower()
            # Whole-phrase match (single correct assignment)
            phrase_match = re.search(r'\b' + re.escape(item_l) + r'\b', s_l)
            # All tokens as separate words
            tokens = item_l.split()
            token_matches = all(re.search(r'\b' + re.escape(tok) + r'\b', s_l) for tok in tokens)
            # Only allow multi-word partial matches for true multi-token phrases and enforce minimum phrase length
            if phrase_match or (len(tokens) > 1 and len(item_l) > 4 and token_matches):
                # Allow generic terms if a specific failure was found in the sentence
                allow_generic = has_generic and has_failure_context
                if item in generic_skip and not allow_generic:
                    continue
                name = item.upper()
                norm = normalize_name(name)
                if norm not in extracted_names:
                    ents.append({
                        "entity_type": entity_type,
                        "entity_name": name,
                        "role": entity_type,
                        "text": sentence
                    })
                    extracted_names.add(norm)
    return ents


# ---------------------------------------------------------
# BIOMEDICAL DOMAIN (CLEAN PIPELINE)
# ---------------------------------------------------------
def extract_biomedical_entities(sentence: str, extracted_names: set, SEEDS_DIR=None) -> list[dict]:
    ents = []
    # 1. COMPOUNDS (use extract_compounds to avoid duplication)
    compounds = extract_compounds(sentence, SEEDS_DIR)
    for c in compounds:
        norm = normalize_name(c["entity_name"])
        if norm not in extracted_names:
            ents.append(c)
            extracted_names.add(norm)

    # 2. TARGETS (use extract_targets to avoid duplication)
    targets = extract_targets(sentence, SEEDS_DIR)
    for t in targets:
        norm = normalize_name(t["entity_name"])
        if norm not in extracted_names:
            ents.append(t)
            extracted_names.add(norm)

    # 3. STEM CELLS — must run BEFORE models to win deduplication for MSC/iPSC/HSC etc.
    for k in STEM_CELL_KEYWORDS:
        if re.search(r'\b' + re.escape(k) + r'\b', sentence, re.IGNORECASE):
            name = k.upper()
            norm = normalize_name(name)
            if norm not in extracted_names:
                ents.append({
                    "entity_type": "stem_cell",
                    "entity_name": name,
                    "entity_variant": "stem_cell",
                    "text": sentence
                })
                extracted_names.add(norm)

    # 4. NEURAL CELLS — must run BEFORE models to win deduplication for neuron/neurons/microglia
    for k in NEURAL_CELL_KEYWORDS:
        if re.search(r'\b' + re.escape(k) + r'\b', sentence, re.IGNORECASE):
            name = k.upper()
            norm = normalize_name(name)
            if norm not in extracted_names:
                ents.append({"entity_type": "neural_cell", "entity_name": name,
                             "entity_variant": "neural_cell", "text": sentence})
                extracted_names.add(norm)

    # 5. MODELS — after stem/neural cells so dedup blocks their overlap terms
    for m in extract_models(sentence, SEEDS_DIR=SEEDS_DIR):
        norm = normalize_name(m["entity_name"])
        if norm not in extracted_names:
            ents.append(m)
            extracted_names.add(norm)

    # 6. PEPTIDES
    for seq in extract_presented_sequences(sentence):
        norm = normalize_name(seq)
        if is_probable_peptide(seq, sentence) and norm not in extracted_names:
            ents.append({"entity_type": "peptide", "entity_name": seq,
                         "entity_variant": "sequence", "role": "tested", "text": sentence})
            extracted_names.add(norm)
    return ents