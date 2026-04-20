"""
Scoring and confidence logic for export pipeline
"""


import logging
from typing import Optional

MODEL_CONTEXT_TERMS = frozenset([
    # Biomedical context terms
    "in vivo", "in vitro", "human", "rat", "mouse", "plasma", "serum",
    "blood", "tissue", "cell culture", "fbs",
    # Construction science context terms
    "site test", "load test", "structural analysis", "field trial", "field test",
    "lab test", "material test", "failure analysis", "environmental exposure", "hazard assessment"
])

def safe_confidence_boost(entities_str: str, current_conf: str, domain_id: Optional[str] = None) -> str:
    """
    Safe confidence promotion rule:
    Promote to HIGH if event has:
    - (domain-relevant entities) AND
    - assay AND
    - model context (in vivo/in vitro/human/rat/plasma/serum)
    """
    conf_normalized = current_conf.lower().strip() if current_conf else "low"
    conf_map = {
        "high": "high",
        "med": "med",
        "medium": "med",
        "low": "low",
        "": "low",
        "none": "low"
    }
    if conf_normalized not in conf_map:
        return "other"
    conf_normalized = conf_map[conf_normalized]
    if conf_normalized == "high":
        return "high"
    if not entities_str:
        return conf_normalized
    entities = entities_str.split("; ")
    entity_types = set()
    entity_names_lower = set()
    for e in entities:
        if ":" in e:
            etype, ename = e.split(":", 1)
            entity_types.add(etype.lower())
            entity_names_lower.add(ename.lower())
        else:
            logging.warning(
                "Malformed entity entry (missing ':'): '%s' in entities_str='%s'",
                e, entities_str
            )
    if domain_id == "construction_science":
        has_high_value = bool(entity_types & {"material", "system", "failure_mode", "environment", "hazard"})
    else:
        has_high_value = bool(entity_types & {"compound", "target", "stem_cell"})
    has_assay = "assay" in entity_types
    has_model_context = bool(entity_names_lower & MODEL_CONTEXT_TERMS)
    if has_high_value and has_assay and has_model_context:
        return "high"
    if has_high_value and has_assay and conf_normalized == "low":
        return "med"
    return conf_normalized
