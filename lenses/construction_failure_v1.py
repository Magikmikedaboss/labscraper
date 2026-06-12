# lenses/construction_failure_v1.py
from __future__ import annotations

from typing import Any, List, Tuple, Optional
from .construction_common import (
    LensEvent, build_lens_event, contains_any, has_unit_signal, has_number, make_entity, dedupe_entities, list_hits
)
from utils.domain_router import route_construction_sentence

MOISTURE_FAILURE_MODES = [
    "mold",
    "humidity",
    "condensation",
    "leakage",
    "water damage",
    "moisture damage",
    "water intrusion",
    "moisture intrusion",
    "roof leak",
    "plumbing leak",
]

STRUCTURAL_FAILURE_MODES = [
    "cracking",
    "spalling",
    "buckling",
    "fatigue",
    "settlement",
    "fracture",
    "collapse",
    "seismic",
]

MATERIAL_FAILURE_MODES = [
    "corrosion",
    "delamination",
    "creep",
    "shrinkage",
    "deterioration",
    "degradation",
    "decay",
    "rot",
    "rust",
    "freeze-thaw",
    "weathering",
]

FIRE_FAILURE_MODES = [
    "ignition",
    "fire spread",
    "fire damage",
    "burn damage",
]

FAILURE_MODES = [
    *MOISTURE_FAILURE_MODES,
    *STRUCTURAL_FAILURE_MODES,
    *MATERIAL_FAILURE_MODES,
    *FIRE_FAILURE_MODES,
]

FAILURE_DRIVERS = [
    "overload", "poor detailing", "water intrusion", "freeze-thaw", "thermal cycling",
    "chloride ingress", "carbonation", "humidity", "improper curing", "design error",
    "construction defect", "material defect", "foundation movement", "wind load", "seismic"
]

CAUSAL_MARKERS = ["due to", "caused by", "attributed to", "resulted from", "led to", "because of"]

HIGH_SIGNAL = ["failure", "failed", "collapse", "fracture", "forensic", "root cause"]

INVESTIGATION_CONTEXT_TERMS = [
    "failure",
    "failed",
    "collapse",
    "fracture",
    "crack",
    "cracking",
    "damage",
    "spalling",
    "buckling",
    "delamination",
    "settlement",
    "leakage",
    "mold",
    "corrosion",
    "deterioration",
    "degradation",
    "ignition",
    "fire",
    "burn",
    "loss",
]

CORROSION_FAILURE_CONTEXT_TERMS = [
    "failure",
    "fail",
    "damage",
    "degradation",
    "pit",
    "pitting",
    "crack",
    "cracking",
    "leak",
    "leakage",
    "corroded",
    "rust",
    "breach",
]


def _has_investigation_context(s_l: str) -> bool:
    return "investigation" in s_l and contains_any(s_l, INVESTIGATION_CONTEXT_TERMS)


def _has_corrosion_failure_context(s_l: str) -> bool:
    corrosion_index = s_l.find("corrosion")
    while corrosion_index != -1:
        window_start = max(0, corrosion_index - 80)
        window_end = min(len(s_l), corrosion_index + 120)
        window = s_l[window_start:window_end]
        if "corrosion resistant" not in window and "corrosion-resistant" not in window:
            if contains_any(window, CORROSION_FAILURE_CONTEXT_TERMS):
                return True
        corrosion_index = s_l.find("corrosion", corrosion_index + len("corrosion"))
    return False

def detect(
    sentence: str,
    source_type: str = "research_paper",
    route_decision: Any | None = None,
) -> Tuple[Optional[LensEvent], List[dict]]:
    s_l = sentence.lower()
    entities: List[dict] = []
    if route_decision is None:
        route_decision = route_construction_sentence(s_l)
    if route_decision.decision == "skip":
        return None, []

    mode_hits = [mode for mode in list_hits(s_l, FAILURE_MODES) if mode != "corrosion" or _has_corrosion_failure_context(s_l)]
    driver_hits = list_hits(s_l, FAILURE_DRIVERS)

    has_high_signal = contains_any(s_l, HIGH_SIGNAL)
    has_investigation_context = _has_investigation_context(s_l)
    has_failure_language = bool(mode_hits) or has_high_signal or has_investigation_context
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
    elif has_investigation_context:
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
    if has_investigation_context:
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
    if has_investigation_context:
        tags.append("has_investigation_context")
    if has_unit_signal(s_l): 
        tags.append("has_units")

    return build_lens_event("failure", "failure_analysis", outcome, conf, tags, sentence, source_type), dedupe_entities(entities)
