"""
Entity extraction logic for PDF scraping pipeline.
Includes: extract_presented_sequences, is_probable_peptide, extract_compounds, extract_targets, extract_models, extract_entities, extract_construction_entities, extract_biomedical_entities, STEM_CELL_KEYWORDS.
"""
import re
from utils.common import _get_compound_seeds, _get_target_seeds, _get_model_seeds

# Stem cell / general bio entities (super lightweight v1)
STEM_CELL_KEYWORDS = [
    "msc", "mesenchymal", "ipsc", "pluripotent", "stem cell", "stem-cell",
    "organoid", "differentiation", "reprogramming"
]


# --- Compound extraction ---
def extract_compounds(sentence: str) -> list[dict]:
    compounds = []
    s_l = sentence.lower()
    extracted_names = set()
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

# --- Target extraction ---
def extract_targets(sentence: str) -> list[dict]:
    targets = []
    for target in _get_target_seeds():
        if re.search(r'\b' + re.escape(target) + r'\b', sentence, re.IGNORECASE):
            targets.append({
                "entity_type": "target",
                "entity_name": target.upper(),
                "entity_variant": "protein",
                "role": "target",
                "text": sentence
            })
    return targets

# --- Model extraction ---
def extract_models(sentence: str) -> list[dict]:
    models = []
    s_l = sentence.lower()
    for model in _get_model_seeds():
        if re.search(r'\b' + re.escape(model) + r'\b', s_l):
            variant = "unknown"
            if any(char.isdigit() for char in model) or '-' in model:
                variant = "cell_line"
            elif model in ["mouse", "mice", "rat", "rats", "human", "humans", "rabbit", "guinea pig", \
                          "hamster", "zebrafish", "drosophila", "c. elegans", "xenopus", "primate", \
                          "pig", "dog"]:
                variant = "organism"
            elif model in ["serum", "plasma", "blood", "csf", "cerebrospinal fluid", "urine", \
                          "saliva", "synovial fluid", "peritoneal fluid", "ascites"]:
                variant = "biofluid"
            elif model in ["liver", "kidney", "heart", "brain", "lung", "spleen", "muscle", \
                          "adipose", "pancreas", "intestine", "colon", "stomach", "skin", "bone", "cartilage"]:
                variant = "tissue"
            elif "organoid" in model or "spheroid" in model or "3d" in model:
                variant = "3d_model"
            models.append({
                "entity_type": "model",
                "entity_name": model.upper() if model.isupper() or len(model) <= 5 else model.capitalize(),
                "entity_variant": variant,
                "text": sentence
            })

    # Fallback: extract common model terms even if not in seeds
    fallback_models = [
        "mouse", "mice", "rat", "rats", "human", "humans", "rabbit", "guinea pig",
        "hamster", "zebrafish", "drosophila", "c. elegans", "xenopus", "primate",
        "pig", "dog", "HEK293", "293T", "CHO", "COS-7", "HeLa", "U2OS", "SH-SY5Y"
    ]
    for fm in fallback_models:
        if re.search(r'\b' + re.escape(fm.lower()) + r'\b', s_l):
            variant = "cell_line" if any(char.isdigit() for char in fm) or '-' in fm or fm.isupper() else "organism"
            models.append({
                "entity_type": "model",
                "entity_name": fm.upper() if fm.isupper() or len(fm) <= 5 else fm.capitalize(),
                "entity_variant": variant,
                "text": sentence
            })
    return models
# --- Entity extraction (domain aware) ---
def extract_entities(sentence: str, domain: str = "methods_tooling") -> list[dict]:
    ents = []
    extracted_names = set()
    if domain == "construction_science":
        ents.extend(extract_construction_entities(sentence, extracted_names))
    else:
        ents.extend(extract_biomedical_entities(sentence, extracted_names))
    return ents

def extract_construction_entities(sentence: str, extracted_names: set) -> list[dict]:
    ents = []
    s_l = sentence.lower()
    construction_materials = {
        "concrete", "steel", "wood", "timber", "brick", "stone", "glass", "plastic",
        "aluminum", "copper", "iron", "composite", "polymer", "ceramic", "asphalt"
    }
    construction_systems = {
        "foundation", "wall", "roof", "floor", "beam", "column", "truss", "frame",
        "slab", "panel", "cladding", "insulation", "ventilation", "plumbing", "electrical"
    }
    environmental_exposures = {
        "temperature", "humidity", "moisture", "rain", "snow", "wind", "sunlight",
        "UV", "freeze", "thaw", "corrosion", "rust", "mold", "mildew", "fungi"
    }
    failure_modes = {
        "crack", "cracking", "fracture", "break", "failure", "collapse", "buckling",
        "deflection", "deformation", "creep", "fatigue", "deterioration", "degradation"
    }
    hazards = {
        "fire", "earthquake", "flood", "wind", "seismic", "impact", "blast", "explosion"
    }
    test_methods = {
        "compression", "tension", "bending", "shear", "torsion", "impact", "fatigue",
        "corrosion", "weathering", "thermal", "fire", "seismic", "load", "stress", "strain"
    }
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
    ents = []
    s_l = sentence.lower()
    # Compound extraction
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

    # Target extraction
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

    # Model extraction
    for e in extract_models(sentence):
        name_lower = e["entity_name"].lower()
        if any(neural in name_lower for neural in ["neuron", "neurons", "microglia", "astrocyte", "astrocytes"]):
            e["entity_type"] = "neural_cell"
        if e["entity_name"] not in extracted_names:
            e["text"] = sentence
            ents.append(e)
            extracted_names.add(e["entity_name"])

    # Explicit neural cell extraction
    neural_cell_terms = ["neuron", "neurons", "microglia", "astrocyte", "astrocytes"]
    for nc in neural_cell_terms:
        if re.search(r'\b' + re.escape(nc) + r'\b', s_l):
            name = nc.upper()
            if name not in extracted_names:
                ents.append({
                    "entity_type": "neural_cell",
                    "entity_name": name,
                    "entity_variant": None,
                    "role": "tested",
                    "text": sentence
                })
                extracted_names.add(name)
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
    # extract_presented_sequences and is_probable_peptide must be implemented
    # presented_seqs = extract_presented_sequences(sentence)
    # for seq in presented_seqs:
    #     if is_probable_peptide(seq, sentence) and seq not in extracted_names:
    #         ents.append({
    #             "entity_type": "peptide",
    #             "entity_name": seq,
    #             "entity_variant": None,
    #             "role": "tested",
    #             "text": sentence
    #         })
    #         extracted_names.add(seq)
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
    for e in extract_models(sentence):
        name_lower = e["entity_name"].lower()
        if any(neural in name_lower for neural in ["neuron", "neurons", "microglia", "astrocyte", "astrocytes"]):
            e["entity_type"] = "neural_cell"
        if e["entity_name"] not in extracted_names:
            e["text"] = sentence
            ents.append(e)
            extracted_names.add(e["entity_name"])
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
