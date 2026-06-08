# lenses/construction_failure_v1.py
from __future__ import annotations

from typing import List, Tuple, Optional
from .construction_common import (
    LensEvent, build_lens_event, contains_any, has_unit_signal, has_number, make_entity, dedupe_entities, list_hits
)

FAILURE_MODES = [
    "cracking", "spalling", "buckling", "fatigue", "corrosion", "delamination",
    "creep", "shrinkage", "settlement", "leakage", "mold", "fracture", "collapse"
]

FAILURE_DRIVERS = [
    "overload", "poor detailing", "water intrusion", "freeze-thaw", "thermal cycling",
    "chloride ingress", "carbonation", "humidity", "improper curing", "design error",
    "construction defect", "material defect", "foundation movement", "wind load", "seismic"
]

CAUSAL_MARKERS = ["due to", "caused by", "attributed to", "resulted from", "led to", "because of"]

HIGH_SIGNAL = ["failure", "failed", "collapse", "fracture", "investigation", "forensic", "root cause"]

def detect(sentence: str, source_type: str = "research_paper") -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []

    mode_hits = list_hits(s_l, FAILURE_MODES)
    driver_hits = list_hits(s_l, FAILURE_DRIVERS)

    has_high_signal = contains_any(s_l, HIGH_SIGNAL)
    has_failure_language = bool(mode_hits) or has_high_signal
    has_causal = any(m in s_l for m in CAUSAL_MARKERS)

    if not has_failure_language and not has_causal:
        return None, []

    # Entities
    for m in mode_hits:
        entities.append(make_entity("failure_mode", m, "failure_mode", "failure"))

    for d in driver_hits[:5]:
        entities.append(make_entity("failure_driver", d, "driver", "cause"))

    # Outcome values: 'failed', 'negative', or 'unknown' (normalized later if needed)
    # Causal language alone is not enough to mark a failure outcome.
    if mode_hits:
        outcome = "failed"
    elif has_high_signal:
        outcome = "negative"
    else:
        outcome = "unknown"

    # Confidence
    score = 0
    if mode_hits:
        score += 2
    if driver_hits:
        score += 2
    if has_causal: 
        score += 1
    if has_number(s_l): 
        score += 1
    if has_unit_signal(s_l): 
        score += 1

    conf = "high" if score >= 6 else "med" if score >= 3 else "low"

    tags = ["failure_analysis"]
    if mode_hits:
        tags.append("has_failure_mode")
    if driver_hits:
        tags.append("has_failure_driver")
    if has_causal: 
        tags.append("has_causality")
    if has_unit_signal(s_l): 
        tags.append("has_units")

    return build_lens_event("failure", "failure_analysis", outcome, conf, tags, sentence, source_type), dedupe_entities(entities)
