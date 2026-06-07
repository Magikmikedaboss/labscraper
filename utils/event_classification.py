"""Core event classification utilities used by scraping pipelines and tests."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List


METHOD_TAGS = {
    "lc-ms/ms": ["lc-ms/ms", "lc ms/ms", "lc-ms", "mass spectrometry", "ms/ms", "mass spec"],
    "mass_spec": ["mass spectrometry", "mass spec", "ms", "ms/ms"],
    "fluorescent": ["fluorescent", "fluorescence", "fluorophore", "label"],
    "serum": ["serum", "plasma", "biological fluids"],
    "incubation": ["incubation", "long incubation"],
    "nitrosamine": ["nitrosamine", "nitrosamines"],
    "gmp": ["gmp", "good manufacturing practice"],
}


FAILURE_PHRASES = {
    "stability_failure": ["rapidly degraded", "degraded", "unstable", "poor stability", "short half-life"],
    "no_activity": ["no significant", "no measurable", "did not show", "no activity", "inactive"],
    "toxicity_flag": ["cytotoxic", "toxicity", "cell death", "toxic"],
    "reproducibility": [
        "not reproducible",
        "poor reproducibility",
        "lack of reproducibility",
        "irreproducible",
        "failed reproducibility",
    ],
    "scalability": ["scale-up", "scalable", "manufacturing", "yield", "process", "costly to produce"],
    "regulatory": ["regulatory", "guideline", "compliance", "safety concern", "risk assessment"],
}


DECISION_PHRASES = {
    "abandoned": ["not pursued", "not pursued further", "excluded", "discarded", "abandoned", "dropped"],
    "modified": ["optimized", "modified", "analog", "derivative", "cyclized", "pegylated", "amidated", "redesigned"],
    "continued": ["further study", "continued", "follow-up", "subsequently", "next we", "we decided", "decided to", "chose to"],
    "paused": ["inconclusive", "unclear", "requires further investigation", "pending"],
    "replicated": ["replicated", "repeated", "validated", "confirmed"],
    "escalated": ["advanced to", "moved to", "progressed to"],
}


OUTCOME_PHRASES = {
    "negative": [
        "no significant",
        "no measurable",
        "inactive",
        "excluded",
        "not pursued",
        "did not",
        "failed to",
        "no improvement",
        "worsened",
        "decreased",
        "declined",
        "degradation",
        "toxic",
        "toxicity",
        "adverse",
    ],
    "positive": [
        "improved",
        "increased",
        "enhanced",
        "more stable",
        "longer half-life",
        "better",
        "higher",
        "greater",
        "successful",
        "showed activity",
        "demonstrated",
        "significant",
    ],
    "neutral": ["moderate", "marginal", "partial", "mixed", "limited", "trend"],
}


HIGH_SIGNAL_TERMS = (
    "lc-ms",
    "mass spectrometry",
    "in vivo",
    "in vitro",
    "clinical",
    "ic50",
    "ec50",
    "half-life",
    "degraded",
    "stable",
    "toxic",
    "efficacy",
    "optimized",
    "modified",
    "abandoned",
    "continued",
)


HIGH_CONF_THRESHOLD = 6
MED_CONF_THRESHOLD = 3


@dataclass(frozen=True)
class ConfidenceInput:
    has_entity: bool
    method_tags: List[str]
    failure_reason: str
    decision_taken: str
    has_measurements: bool
    sentence_l: str = ""


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"\b" + re.escape(phrase) + r"\b", text) is not None


def detect_method_tags(sentence_l: str) -> List[str]:
    tags: List[str] = []
    for tag, phrases in METHOD_TAGS.items():
        if any(_contains_phrase(sentence_l, p) for p in phrases):
            tags.append(tag)
    return tags


def detect_failure_reason(sentence_l: str) -> str:
    for reason, phrases in FAILURE_PHRASES.items():
        if any(_contains_phrase(sentence_l, p) for p in phrases):
            return reason
    return "unknown"


def detect_decision(sentence_l: str) -> str:
    # Future decision metadata can be added later, but the public API stays single-value for now.
    for decision, phrases in DECISION_PHRASES.items():
        if any(_contains_phrase(sentence_l, p) for p in phrases):
            return decision
    return "unknown"


def detect_outcome(sentence_l: str) -> str:
    for outcome in ("negative", "positive", "neutral"):
        if any(_contains_phrase(sentence_l, p) for p in OUTCOME_PHRASES[outcome]):
            return outcome
    return "unknown"


def classify_event_type(sentence_l: str, method_tags: List[str], failure_reason: str, decision_taken: str) -> str:
    s = sentence_l
    if "nitrosamine" in method_tags or failure_reason == "regulatory":
        return "regulatory_risk"
    if failure_reason == "toxicity_flag" or any(_contains_phrase(s, k) for k in ("toxic", "toxicity", "cytotoxic")):
        return "toxicity_flag"
    if failure_reason == "stability_failure":
        return "stability_issue"
    if any(_contains_phrase(s, k) for k in ("degradation", "degraded", "corrosion", "instability", "unstable", "poor stability")):
        return "degradation_event"
    if failure_reason == "no_activity" or any(_contains_phrase(s, k) for k in ("activity", "efficacy", "potent", "ic50", "ec50")):
        return "efficacy_result"
    if failure_reason == "scalability" or any(_contains_phrase(s, k) for k in ("manufacturing", "scale-up", "yield", "production")):
        return "manufacturing_constraint"
    if method_tags:
        if any(_contains_phrase(s, k) for k in ("cost-intensive", "expensive", "time-consuming", "efficient", "cost-effective")):
            return "cost_tradeoff"
        return "method_evaluation"
    if decision_taken != "unknown":
        return "decision_point"
    return "other"


def evidence_strength(sentence_l: str) -> str:
    sentence_lower = sentence_l.lower()
    strong_terms = ("we conclude", "demonstrate", "significant", "robust", "strong")
    weak_terms = ("suggest", "may", "might", "could", "trend")

    strong_pattern = r"\b(?:" + "|".join(re.escape(term) for term in strong_terms) + r")\b"
    weak_pattern = r"\b(?:" + "|".join(re.escape(term) for term in weak_terms) + r")\b"

    if re.search(strong_pattern, sentence_lower):
        return "strong"
    if re.search(weak_pattern, sentence_lower):
        return "weak"
    return "moderate"


def confidence_score(input_data: ConfidenceInput) -> str:
    """Return low/med/high confidence from a ConfidenceInput instance."""
    if not isinstance(input_data, ConfidenceInput):
        raise TypeError("confidence_score requires a ConfidenceInput instance")
    ci = input_data

    score = 0
    if ci.has_entity:
        score += 2
    if ci.method_tags:
        score += 1
    if ci.failure_reason != "unknown":
        score += 2
    if ci.decision_taken != "unknown":
        score += 1
    if ci.has_measurements:
        score += 2

    signal_count = sum(1 for term in HIGH_SIGNAL_TERMS if _contains_phrase(ci.sentence_l, term))
    if signal_count >= 3:
        score += 2
    elif signal_count >= 2:
        score += 1

    if score >= HIGH_CONF_THRESHOLD:
        return "high"
    if score >= MED_CONF_THRESHOLD:
        return "med"
    return "low"


def suggested_keep(conf: str, event_type: str, failure_reason: str, decision_taken: str, tags: List[str]) -> int:
    if conf in ("med", "high"):
        return 1
    if event_type != "other" and (
        failure_reason != "unknown" or decision_taken != "unknown" or bool(tags)
    ):
        return 1
    return 0
