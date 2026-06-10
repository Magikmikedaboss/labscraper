from __future__ import annotations

from dataclasses import dataclass
import re


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().split())


def _collect_matches(text: str, patterns: list[tuple[str, list[str], int]]) -> tuple[list[str], int]:
    normalized = _normalize_text(text)
    matches: list[str] = []
    score = 0
    for label, phrases, weight in patterns:
        for phrase in phrases:
            normalized_phrase = _normalize_text(phrase)
            if normalized_phrase and re.search(r"\b" + re.escape(normalized_phrase) + r"\b", normalized):
                matches.append(label)
                score += weight
                break
    return sorted(set(matches)), score


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    normalized = _normalize_text(text)
    hits = 0
    for keyword in keywords:
        if _normalize_text(keyword) in normalized:
            hits += 1
    return min(hits * 2, 10)


CONSTRUCTION_SENTENCE_PATTERNS = [
    ("building envelope", ["building envelope", "air barrier", "thermal bridge"], 4),
    ("moisture", ["moisture", "water intrusion", "water leakage", "condensation", "wetting", "vapor barrier", "air sealing"], 3),
    ("roof", ["roof", "roofing", "roof assembly"], 2),
    ("wall", ["wall", "wall assembly", "wall system", "enclosure assembly", "building components", "facade", "façade", "cladding"], 2),
    ("foundation", ["foundation", "slab", "basement", "footing"], 2),
    ("materials", ["concrete", "steel", "masonry", "timber", "wood", "insulation"], 2),
    ("structural", ["structural", "load bearing", "load-bearing"], 2),
    ("codes", ["astm", "aci", "asce", "ibc", "irc", "iecc", "ashrae", "nfpa", "ul", "icc", "iso", "eurocode"], 3),
    ("code phrases", ["building code", "code compliance", "code requirement", "code provisions", "code standard"], 4),
    ("building", ["building", "construction", "building science", "building science corporation"], 1),
    ("component", ["beam", "column", "attic", "crawlspace"], 1),
]


@dataclass(frozen=True)
class RouteDecision:
    decision: str
    reason: str
    construction_score: int
    contamination_score: int
    physics_score: int
    materials_score: int
    construction_signals: tuple[str, ...]
    contamination_signals: tuple[str, ...]


@dataclass(frozen=True)
class SentenceRouteDecision:
    decision: str
    reason: str
    construction_score: int
    construction_signals: tuple[str, ...]


def route_construction_sentence(sentence: str) -> SentenceRouteDecision:
    normalized = _normalize_text(sentence)
    construction_signals, construction_score = _collect_matches(normalized, CONSTRUCTION_SENTENCE_PATTERNS)

    if construction_score >= 2:
        decision = "keep"
        reason = f"construction sentence detected; construction={construction_score}"
    else:
        decision = "skip"
        reason = f"construction signal too weak; construction={construction_score}"

    return SentenceRouteDecision(
        decision=decision,
        reason=reason,
        construction_score=construction_score,
        construction_signals=tuple(construction_signals),
    )


def route_construction_source(*, title: str = "", text: str = "", url: str = "") -> RouteDecision:
    combined_text = "\n".join(part for part in (title, text, url) if part)

    # lazy import to avoid circular dependency with utils.source_triage
    from utils.source_triage import (
        BUILDING_CONTEXT_PATTERNS,
        CONSTRUCTION_PATTERNS,
        CONTAMINATION_PATTERNS,
        MATERIALS_RESEARCH_KEYWORDS,
        PHYSICS_RESEARCH_KEYWORDS,
    )

    construction_signals, construction_score = _collect_matches(combined_text, CONSTRUCTION_PATTERNS)
    building_context_signals, building_context_score = _collect_matches(combined_text, BUILDING_CONTEXT_PATTERNS)
    contamination_signals, contamination_score = _collect_matches(combined_text, CONTAMINATION_PATTERNS)
    physics_score = _keyword_score(combined_text, PHYSICS_RESEARCH_KEYWORDS)
    materials_score = _keyword_score(combined_text, MATERIALS_RESEARCH_KEYWORDS)

    construction_strength = max(construction_score, building_context_score)
    if contamination_score >= 2 and contamination_score > construction_strength and not building_context_signals:
        decision = "skip"
    elif construction_strength >= 4 or materials_score >= 4 or physics_score >= 4:
        decision = "keep"
    else:
        decision = "review"

    if decision == "skip":
        reason = (
            f"biomedical contamination dominates; construction={construction_strength}, "
            f"contamination={contamination_score}, physics={physics_score}, materials={materials_score}"
        )
    elif decision == "keep":
        reason = (
            f"construction signal present; construction={construction_strength}, "
            f"contamination={contamination_score}, physics={physics_score}, materials={materials_score}"
        )
    else:
        reason = (
            f"mixed/weak source metadata; construction={construction_strength}, "
            f"contamination={contamination_score}, physics={physics_score}, materials={materials_score}"
        )

    return RouteDecision(
        decision=decision,
        reason=reason,
        construction_score=construction_strength,
        contamination_score=contamination_score,
        physics_score=physics_score,
        materials_score=materials_score,
        construction_signals=tuple(construction_signals + building_context_signals),
        contamination_signals=tuple(contamination_signals),
    )
