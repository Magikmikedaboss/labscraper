
import logging
import re
from typing import Optional

# Configurable mapping of high-value entity types by domain
HIGH_VALUE_ENTITY_TYPES_BY_DOMAIN = {
    "construction_science": {"material", "system", "failure_mode", "environment", "hazard"},
    # Add more domains as needed
}
# Biomedical-specific high-value types. Keep this out of the global fallback path so unknown
# or non-biomedical domains do not inherit biomedical confidence boosts by accident.
DEFAULT_HIGH_VALUE_SET = {"compound", "target", "stem_cell"}
# Domains that are allowed to use the biomedical fallback set when they have no explicit
# high-value mapping of their own.
BIOMED_DOMAINS = {
    "methods_tooling",
    "drug_discovery",
    "biohacking_longevity",
    "neuroscience_cognition",
    "stem_cells_regen",
}
"""
Scoring and confidence logic for export pipeline
"""

# ---
# Confidence normalization for system boundaries
def normalize_confidence(conf: str) -> str:
    """Normalize confidence to 'low', 'med', or 'high'. Unknowns become 'low'."""
    conf = conf.lower()
    if conf not in {"low", "med", "high"}:
        return "low"
    return conf


MODEL_CONTEXT_TERMS = frozenset([
    # Biomedical context terms
    "in vivo", "in vitro", "human", "rat", "mouse", "plasma", "serum",
    "blood", "tissue", "cell culture", "fbs",

    # Construction science context terms
    "site test", "load test", "structural analysis", "field trial",
    "field test", "lab test", "material test", "failure analysis",
    "environmental exposure", "hazard assessment"
])

MODEL_CONTEXT_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in MODEL_CONTEXT_TERMS) + r")\b"
)


def safe_confidence_boost(
    entities_str: str,
    current_conf: str,
    domain_id: Optional[str] = None,
    sentence_l: Optional[str] = None,
) -> str:
    """
    Safe confidence promotion rule.

    Promotes confidence based on:
    - entity types (domain-aware)
    - assay/test presence
    - contextual language in sentence
    """

    # ---------------------------------------------------------
    # Normalize confidence
    # ---------------------------------------------------------
    raw_conf = (current_conf or "low").strip().lower()

    conf_map = {
        "high": "high",
        "med": "med",
        "medium": "med",
        "low": "low",
        "": "low",
        "none": "low",
    }

    # Fallback to "low" for unknown values
    conf_normalized = conf_map.get(raw_conf, "low")
    if conf_normalized == "high":
        return "high"

    # ---------------------------------------------------------
    # Parse entities safely
    # ---------------------------------------------------------
    if not entities_str:
        return conf_normalized

    # Split more safely
    raw_entities = [e.strip() for e in entities_str.split(";") if e.strip()]

    entity_types = set()
    entity_names_lower = set()

    for e in raw_entities:
        if ":" in e:
            etype, ename = e.split(":", 1)
            etype = etype.lower().strip()
            ename = ename.lower().strip()
            if not etype or not ename:
                logging.warning(
                    "Malformed entity entry with empty type or name: '%s' in entities_str='%s'",
                    e, entities_str
                )
                continue
            entity_types.add(etype)
            entity_names_lower.add(ename)
        else:
            logging.warning(
                "Malformed entity entry (missing ':'): '%s' in entities_str='%s'",
                e, entities_str
            )


    # ---------------------------------------------------------
    # Domain-aware scoring (edit HIGH_VALUE_ENTITY_TYPES_BY_DOMAIN to change rules)
    # ---------------------------------------------------------
    high_value_set = HIGH_VALUE_ENTITY_TYPES_BY_DOMAIN.get(domain_id, set())
    if not high_value_set and domain_id in BIOMED_DOMAINS:
        high_value_set = DEFAULT_HIGH_VALUE_SET
    has_high_value = bool(entity_types & high_value_set)

    # "assay" doesn't exist in construction → expand meaning
    has_assay = (
        "assay" in entity_types or
        "test_method" in entity_types or
        "measurement" in entity_types
    )

    # ---------------------------------------------------------
    # Sentence context
    # ---------------------------------------------------------
    sentence_lower = sentence_l.lower() if isinstance(sentence_l, str) else ""

    has_model_context = bool(MODEL_CONTEXT_PATTERN.search(sentence_lower))

    # ---------------------------------------------------------
    # Confidence logic
    # ---------------------------------------------------------
    if has_high_value and has_assay and has_model_context:
        return "high"

    if has_high_value and has_assay:
        return "med"

    # Light boost
    if has_high_value and conf_normalized == "low":
        return "med"

    return conf_normalized