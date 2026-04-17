import re
from utils.common import _get_compound_seeds, _get_target_seeds, _get_model_seeds


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def normalize_name(name: str) -> str:
    """Normalize entity name for deduplication."""
    return re.sub(r'[\s\-_,.;:]+', '', name.strip().lower())


STEM_CELL_KEYWORDS = [
    "msc", "mesenchymal", "ipsc", "pluripotent",
    "stem cell", "stem-cell", "organoid",
    "differentiation", "reprogramming"
]

NEURAL_CELL_KEYWORDS = [
    "neuron", "neurons", "dopaminergic", "glutamatergic", "gabaergic", "astrocyte", "astrocytes", "oligodendrocyte", "oligodendrocytes", "microglia", "microglial"
]


# ---------------------------------------------------------
# COMPOUNDS
# ---------------------------------------------------------
def extract_compounds(sentence: str, SEEDS_DIR=None) -> list[dict]:
    compounds = []
    seen = set()
    for compound in _get_compound_seeds(SEEDS_DIR):
        if re.search(r'\b' + re.escape(compound) + r'\b', sentence, re.IGNORECASE):
            name = compound.upper()
            if name not in seen:
                compounds.append({
                    "entity_type": "compound",
                    "entity_name": name,
                    "entity_variant": "drug",
                    "role": "tested",
                    "text": sentence
                })
                seen.add(name)
    return compounds


# ---------------------------------------------------------
# TARGETS
# ---------------------------------------------------------
def extract_targets(sentence: str, SEEDS_DIR=None) -> list[dict]:
    targets = []
    seen_target_names = set()
    for target in _get_target_seeds(SEEDS_DIR):
        norm_name = target.upper()
        if re.search(r'\b' + re.escape(target) + r'\b', sentence, re.IGNORECASE) and norm_name not in seen_target_names:
            targets.append({
                "entity_type": "target",
                "entity_name": norm_name,
                "entity_variant": "protein",
                "role": "target",
                "text": sentence
            })
            seen_target_names.add(norm_name)
    return targets


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------
def extract_models(sentence: str, SEEDS_DIR=None) -> list[dict]:
    models = []
    for model in _get_model_seeds(SEEDS_DIR):
        if re.search(r'\b' + re.escape(model) + r'\b', sentence, re.IGNORECASE):
            variant = "unknown"
            if any(c.isdigit() for c in model) or '-' in model:
                variant = "cell_line"
            elif model in ["mouse", "mice", "rat", "human"]:
                variant = "organism"
            elif "organoid" in model or "3d" in model:
                variant = "3d_model"
            models.append({
                "entity_type": "model",
                "entity_name": model.upper(),
                "entity_variant": variant,
                "text": sentence
            })
    fallback_models = ["mouse", "rat", "human", "hela", "hek293"]
    for fm in fallback_models:
        if re.search(r'\b' + re.escape(fm) + r'\b', sentence, re.IGNORECASE):
            models.append({
                "entity_type": "model",
                "entity_name": fm.upper(),
                "entity_variant": "organism",
                "text": sentence
            })
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
        return extract_construction_entities(sentence, extracted_names)
    return extract_biomedical_entities(sentence, extracted_names, SEEDS_DIR=SEEDS_DIR)


# ---------------------------------------------------------
# CONSTRUCTION DOMAIN
def extract_construction_entities(sentence: str, extracted_names: set) -> list[dict]:
    ents = []
    s_l = sentence.lower()

    materials = {"concrete", "steel", "wood", "glass"}
    systems = {"wall", "roof", "foundation"}
    failures = {"crack", "fracture", "collapse"}

    for group, entity_type in [
        (materials, "material"),
        (systems, "system"),
        (failures, "failure_mode")
    ]:
        for item in group:
            if item in s_l:
                name = item.upper()
                norm = normalize_name(name)

                if norm not in extracted_names:
                    ents.append({
                        "entity_type": entity_type,
                        "entity_name": name,
                        "role": entity_type
                    })
                    extracted_names.add(norm)

    return ents


# ---------------------------------------------------------
# BIOMEDICAL DOMAIN (CLEAN PIPELINE)
# ---------------------------------------------------------
def extract_biomedical_entities(sentence: str, extracted_names: set, SEEDS_DIR=None) -> list[dict]:
    ents = []
    # 1. COMPOUNDS
    for compound in _get_compound_seeds(SEEDS_DIR):
        if re.search(r'\b' + re.escape(compound) + r'\b', sentence, re.IGNORECASE):
            name = compound.upper()
            norm = normalize_name(name)
            if norm not in extracted_names:
                ents.append({
                    "entity_type": "compound",
                    "entity_name": name,
                    "entity_variant": "drug",
                    "role": "tested",
                    "text": sentence
                })
                extracted_names.add(norm)
    # 2. TARGETS
    for target in _get_target_seeds(SEEDS_DIR):
        if re.search(r'\b' + re.escape(target) + r'\b', sentence, re.IGNORECASE):
            name = target.upper()
            norm = normalize_name(name)
            if norm not in extracted_names:
                ents.append({
                    "entity_type": "target",
                    "entity_name": name,
                    "entity_variant": "protein",
                    "role": "target",
                    "text": sentence
                })
                extracted_names.add(norm)
    # 3. MODELS
    models = []
    for model in _get_model_seeds(SEEDS_DIR):
        if re.search(r'\b' + re.escape(model) + r'\b', sentence, re.IGNORECASE):
            variant = "unknown"
            if any(c.isdigit() for c in model) or '-' in model:
                variant = "cell_line"
            elif model in ["mouse", "mice", "rat", "human"]:
                variant = "organism"
            elif "organoid" in model or "3d" in model:
                variant = "3d_model"
            models.append({
                "entity_type": "model",
                "entity_name": model.upper(),
                "entity_variant": variant,
                "text": sentence
            })
    fallback_models = ["mouse", "rat", "human", "hela", "hek293"]
    for fm in fallback_models:
        if re.search(r'\b' + re.escape(fm) + r'\b', sentence, re.IGNORECASE):
            models.append({
                "entity_type": "model",
                "entity_name": fm.upper(),
                "entity_variant": "organism",
                "text": sentence
            })
    return ents