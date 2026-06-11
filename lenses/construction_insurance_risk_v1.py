from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

from lenses.construction_common import LensEvent, RouteDecision, build_lens_event, dedupe_entities, make_entity

LENS_NAME = "insurance_risk"

LOSS_CAUSES = {
    "water damage",
    "water intrusion",
    "moisture intrusion",
    "wind damage",
    "hail damage",
    "fire damage",
    "flood damage",
    "roof leak",
    "plumbing leak",
    "mold",
    "fire",
    "smoke",
    "hail",
    "wind",
    "flood",
    "storm",
    "freeze damage",
    "collapse",
    "foundation movement",
    "settlement",
}

PROPERTY_RISK_TERMS = {
    "failure",
    "leak",
    "intrusion",
    "rot",
    "corrosion",
    "moisture",
}

BUILDING_SYSTEMS = {
    "roof",
    "wall",
    "foundation",
    "floor",
    "ceiling",
    "attic",
    "crawlspace",
    "basement",
    "siding",
    "stucco",
    "window",
    "door",
    "plumbing",
    "electrical",
    "hvac",
}

BUILDING_CONTEXT = {
    "roof",
    "roofing",
    "shingle",
    "shingles",
    "wall",
    "foundation",
    "building",
    "home",
    "house",
    "attic",
    "window",
    "door",
    "structure",
    "assembly",
    "envelope",
    "siding",
    "basement",
    "property",
}

ALLOWED_SOURCE_TYPES = {"news", "research_paper"}

INSURANCE_TERMS = {
    "claim",
    "claims",
    "loss",
    "losses",
    "damage",
    "covered",
    "coverage",
    "deductible",
    "policy",
    "exclusion",
    "endorsement",
    "adjuster",
    "mitigation",
    "remediation",
    "repair cost",
    "replacement cost",
    "actual cash value",
    "subrogation",
}

MITIGATION_TERMS = {
    "mitigation",
    "risk reduction",
    "risk-reduction",
    "hardening",
    "retrofit",
    "repair",
    "replacement",
    "remediation",
    "drying",
    "drainage",
    "flashing",
    "fire resistant",
    "fire-resistant",
    "impact resistant",
    "impact-resistant",
    "wind resistant",
    "wind-resistant",
}

MITIGATION_POSITIVE_TERMS = {
    "reduced",
    "reduce",
    "reducing",
    "improved",
    "improve",
    "effective",
    "success",
    "successfully",
    "mitigated",
    "lowered",
    "decreased",
    "prevented",
}

MITIGATION_NEGATIVE_TERMS = {
    "failed",
    "ineffective",
    "despite",
    "required remediation",
    "ongoing",
    "insufficient",
    "unresolved",
}

BIOMEDICAL_DENY = {
    "cell",
    "cells",
    "protein",
    "gene",
    "stem cell",
    "clinical",
    "patient",
    "tumor",
    "glioblastoma",
    "organoid",
    "antibody",
    "serum",
}


def _contains_any(text: str, terms: Iterable[str]) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for term in terms:
        if re.search(rf"\b{re.escape(term)}\b", lower):
            found.append(term)
    return found


def _context_strength(entity_count: int) -> str:
    if entity_count >= 4:
        return "strong"
    if entity_count >= 2:
        return "moderate"
    return "weak"


def _build_entities(loss_causes: list[str], systems: list[str], insurance_terms: list[str], mitigation_terms: list[str]) -> list[dict]:
    entities: list[dict] = []

    for item in loss_causes:
        entities.append(make_entity("loss_cause", item, item, "cause"))

    for item in systems:
        entities.append(make_entity("building_system", item, item, "asset"))

    for item in insurance_terms:
        entities.append(make_entity("insurance_term", item, item, "insurance"))

    for item in mitigation_terms:
        entities.append(make_entity("mitigation", item, item, "response"))

    return dedupe_entities(entities)


def _mitigation_hits(lower: str, insurance_terms: list[str]) -> list[str]:
    mitigation_terms = _contains_any(lower, MITIGATION_TERMS)
    # Drop the generic "replacement" mitigation token when the sentence is clearly about replacement claims
    # or coverage language rather than an actionable mitigation measure.
    if _should_drop_replacement(lower, insurance_terms) and "replacement" in mitigation_terms:
        mitigation_terms = [term for term in mitigation_terms if term != "replacement"]
    return mitigation_terms


def _should_drop_replacement(lower: str, insurance_terms: list[str]) -> bool:
    return bool(re.search(r"\breplacement\s+claims?\b", lower) or "replacement cost" in insurance_terms)


def _property_risk_supported(
    property_risk_terms: list[str],
    systems: list[str],
    loss_causes: list[str],
    insurance_terms: list[str],
) -> bool:
    return bool(property_risk_terms and (systems or loss_causes or insurance_terms))


def route_insurance_risk_sentence(sentence: str):
    lower = sentence.lower()

    if _contains_any(lower, BIOMEDICAL_DENY):
        return RouteDecision("skip", "biomedical contamination")

    building_hits = _contains_any(lower, BUILDING_CONTEXT)
    if not building_hits:
        return RouteDecision("skip", "no building context")

    loss_causes = _contains_any(lower, LOSS_CAUSES)
    property_risk_terms = _contains_any(lower, PROPERTY_RISK_TERMS)
    insurance_terms = _contains_any(lower, INSURANCE_TERMS)
    systems = _contains_any(lower, BUILDING_SYSTEMS)
    mitigation_terms = _mitigation_hits(lower, insurance_terms)
    property_risk_supported = _property_risk_supported(property_risk_terms, systems, loss_causes, insurance_terms)

    if not loss_causes and not property_risk_supported and not insurance_terms and not mitigation_terms:
        return RouteDecision("skip", "no insurance-risk signal")

    if not systems and not loss_causes and not property_risk_supported and not mitigation_terms:
        return RouteDecision("skip", "no building or mitigation context")

    return RouteDecision("keep", "insurance-risk signal present")


def _detect_sentence(sentence: str, source_type: str = "research_paper", source_weight: float = 1.0) -> Tuple[Optional[LensEvent], list[dict]]:
    lower = sentence.lower()

    if _contains_any(lower, BIOMEDICAL_DENY):
        return None, []

    building_hits = _contains_any(lower, BUILDING_CONTEXT)
    if not building_hits:
        return None, []

    loss_causes = _contains_any(lower, LOSS_CAUSES)
    property_risk_terms = _contains_any(lower, PROPERTY_RISK_TERMS)
    systems = _contains_any(lower, BUILDING_SYSTEMS)
    insurance_terms = _contains_any(lower, INSURANCE_TERMS)
    mitigation_terms = _mitigation_hits(lower, insurance_terms)
    property_risk_supported = _property_risk_supported(property_risk_terms, systems, loss_causes, insurance_terms)

    if not loss_causes and not property_risk_supported and not insurance_terms and not mitigation_terms:
        return None, []

    if not systems and not loss_causes and not property_risk_supported and not mitigation_terms:
        return None, []

    entities = _build_entities(loss_causes, systems, insurance_terms, mitigation_terms)

    mitigation_positive = _contains_any(lower, MITIGATION_POSITIVE_TERMS)
    mitigation_negative = _contains_any(lower, MITIGATION_NEGATIVE_TERMS)

    if mitigation_terms and mitigation_negative:
        event_type = "risk_mitigation"
        raw_outcome = "degraded"
    elif mitigation_terms and mitigation_positive:
        event_type = "risk_mitigation"
        raw_outcome = "improved"
    elif mitigation_terms:
        event_type = "risk_mitigation"
        raw_outcome = "neutral"
    elif insurance_terms and (loss_causes or property_risk_supported or systems):
        event_type = "claim_driver"
        raw_outcome = "degraded"
    elif property_risk_supported:
        event_type = "property_risk"
        raw_outcome = "degraded"
    else:
        event_type = "property_loss_event"
        raw_outcome = "degraded"

    confidence = "high" if len(entities) >= 3 else "med"
    tags = ["insurance_risk"]
    if loss_causes:
        tags.append("loss_cause")
    if property_risk_supported:
        tags.append("property_risk")
    if systems:
        tags.append("building_system")
    if mitigation_terms:
        tags.append("mitigation")

    event = build_lens_event(
        lens_name=LENS_NAME,
        event_type=event_type,
        raw_outcome=raw_outcome,
        confidence=confidence,
        tags=tags,
        sentence=sentence,
        source_type=source_type,
    )
    # build_lens_event normalizes the shared fields, but insurance-risk uses a compact entity-count heuristic and
    # source_weight scaling so low-event-count claims remain discriminative; this intentionally differs from the
    # default infer_context_strength path used by the other lenses.
    event.context_strength = _context_strength(len(entities))
    event.source_weight = max(0.0, min(1.0, event.source_weight * source_weight))
    return event, entities


def analyze_sentence(
    sentence: str,
    source_weight: float = 1.0,
    source_type: str = "research_paper",
) -> list[LensEvent]:
    event, _ = _detect_sentence(sentence, source_weight=source_weight, source_type=source_type)
    return [event] if event is not None else []


def analyze_text(
    text: str,
    source_weight: float = 1.0,
    source_type: str = "research_paper",
) -> list[LensEvent]:
    events: list[LensEvent] = []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    for sentence in sentences:
        if not sentence:
            continue
        events.extend(analyze_sentence(sentence, source_weight=source_weight, source_type=source_type))
    return events


def detect(sentence: str, source_type: str = "research_paper") -> Tuple[Optional[LensEvent], List[dict]]:
    return _detect_sentence(sentence, source_type=source_type)