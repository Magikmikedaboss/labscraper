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
    "stem cell", "stem-cell",
    # "organoid" REMOVED — typed as model via models.txt
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

    # Expanded and more specific groups (boosted with more keywords)
    groups = [
        ({"concrete", "steel", "wood", "glass", "brick", "timber", "mortar", "insulation", "polymer", "composite", "asphalt", "aluminum", "copper", "gypsum", "plaster", "ceramic", "stone", "aggregate", "fiber", "foam", "bitumen", "PVC", "EPS", "XPS", "HDPE", "LDPE"}, "material"),
        ({"wall", "roof", "foundation", "floor", "column", "beam", "slab", "girder", "truss", "panel", "joint", "window", "door", "façade", "cladding", "insulation system", "partition", "rafter", "stud", "joist", "lintel"}, "system"),
        ({"crack", "cracking", "shear failure", "buckling", "fatigue", "delamination", "fracture", "rupture", "collapse", "spalling", "yielding", "debonding", "creep", "shrinkage", "corrosion fatigue", "brittle fracture", "ductile fracture", "plastic hinge", "instability", "failure mode", "microcrack", "macrocrack"}, "failure_mode"),
        ({"temperature", "thermal cycling", "humidity", "moisture", "wind", "rain", "fire", "freeze", "frost", "uv", "solar", "environmental stress", "exposure", "condensation", "weather", "climate", "precipitation", "snow", "hail", "thermal shock"}, "environment"),
        ({"compression", "tension", "shear", "bending", "torsion", "impact", "flexure", "creep test", "fatigue test", "tensile test", "load test", "stress test", "thermal analysis", "modulus", "stiffness", "ductility", "hardness", "strength", "yield strength", "ultimate strength", "elasticity", "plasticity"}, "test_method"),
        ({"flood", "seismic", "earthquake", "corrosion", "erosion", "vibration", "overload", "fire hazard", "chemical attack", "abrasion", "freeze-thaw", "alkali-silica reaction", "subsidence", "settlement", "liquefaction", "tsunami", "landslide", "storm", "hurricane", "typhoon", "cyclone"}, "hazard"),
    ]

    # Helper: look for multi-word descriptors near generic terms
    def find_specific_failure(sentence):
        # e.g., "shear failure", "fatigue crack", "stress corrosion"
        patterns = [
            r"(shear|fatigue|stress|thermal|brittle|ductile|creep|shrinkage|corrosion) (failure|crack|fracture|collapse|spalling)",
            r"(failure|crack|fracture|collapse|spalling) (due to|from|by) (shear|fatigue|stress|thermal|creep|corrosion)",
            r"([a-z]+) (fracture|crack|failure|collapse)",
            r"(fracture|crack|failure|collapse) of ([a-z]+)"
        ]
        matches = []
        for pat in patterns:
            for m in re.findall(pat, sentence.lower()):
                if isinstance(m, tuple):
                    matches.append(" ".join([w for w in m if w]))
                else:
                    matches.append(m)
        return matches

    # Add specific failures first
    for specific in find_specific_failure(sentence):
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
    for group, entity_type in groups:
        for item in group:
            if item.lower() in s_l or (len(item) > 4 and any(word in s_l for word in item.lower().split())):
                # Allow generic terms if a specific failure was found in the sentence
                allow_generic = any(g in s_l for g in generic_skip) and any(x in s_l for x in ["crack", "fracture", "collapse", "spalling"])
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
    # 1. COMPOUNDS
    for compound in _get_compound_seeds(SEEDS_DIR):
        pattern = r'\b' + re.escape(compound) + r'\b'
        if re.search(pattern, sentence, re.IGNORECASE):
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
        pattern = r'\b' + re.escape(target) + r'\b'
        if re.search(pattern, sentence, re.IGNORECASE):
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

    # 3. STEM CELLS — must run BEFORE models to win deduplication for MSC/iPSC/HSC etc.
    for k in STEM_CELL_KEYWORDS:
        if re.search(r'\b' + re.escape(k) + r'\b', sentence, re.IGNORECASE):
            name = k.upper() if len(k) <= 5 or k.lower() in {"msc", "ipsc", "hsc", "esc", "nsc"} else k
            norm = normalize_name(name)
            if norm not in extracted_names:
                ents.append({"entity_type": "stem_cell", "entity_name": name,
                             "entity_variant": norm, "text": sentence})
                extracted_names.add(norm)

    # 4. NEURAL CELLS — must run BEFORE models to win deduplication for neuron/neurons/microglia
    for k in NEURAL_CELL_KEYWORDS:
        if re.search(r'\b' + re.escape(k) + r'\b', sentence, re.IGNORECASE):
            name = k.upper()
            norm = normalize_name(name)
            if norm not in extracted_names:
                ents.append({"entity_type": "neural_cell", "entity_name": name,
                             "entity_variant": norm, "text": sentence})
                extracted_names.add(norm)

    # 5. MODELS — after stem/neural cells so dedup blocks their overlap terms
    models = []
    for model in _get_model_seeds(SEEDS_DIR):
        if re.search(r'\b' + re.escape(model) + r'\b', sentence, re.IGNORECASE):
            variant = "unknown"
            if any(c.isdigit() for c in model) or '-' in model:
                variant = "cell_line"
            elif model.lower() in {"mouse", "mice", "rat", "human"}:
                variant = "organism"
            elif "organoid" in model.lower() or "3d" in model.lower():
                pass  # No special variant, keep as unknown
            models.append({"entity_type": "model", "entity_name": model.upper(),
                           "entity_variant": variant, "text": sentence})

    for fm in ["mouse", "rat", "human", "hela", "hek293"]:
        if re.search(r'\b' + re.escape(fm) + r'\b', sentence, re.IGNORECASE):
            variant = "cell_line" if fm in ["hela", "hek293"] else "organism"
            models.append({"entity_type": "model", "entity_name": fm.upper(),
                           "entity_variant": variant, "text": sentence})
    for m in models:
        norm = normalize_name(m["entity_name"])
        if norm not in extracted_names:
            ents.append(m)
            extracted_names.add(norm)

    # 6. PEPTIDES
    for seq in extract_presented_sequences(sentence):
        norm = normalize_name(seq)
        if is_probable_peptide(seq, sentence) and norm not in extracted_names:
            ents.append({"entity_type": "peptide", "entity_name": seq,
                         "role": "tested", "text": sentence})
            extracted_names.add(norm)

    return ents