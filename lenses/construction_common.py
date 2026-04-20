from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------- Basic unit / numeric signals ----------
UNIT_PATTERNS = [
    r"\bmpa\b", r"\bkpa\b", r"\bgpa\b",
    r"\bkn\b", r"\bmn\b",
    r"\bmm\b", r"\bcm\b", # r"\bm\b",  # meters (removed: too short, high false positive risk)
    # Removed overly broad 'in' and 'n' patterns to avoid false positives
    r"\bft\b",
    r"\bw/m2k\b", r"\bw/m·k\b", r"\bw/mk\b",
    r"\bwh\b", r"\bkwh\b", r"\bkw\b",
    r"\bpa\b", r"\bppm\b",
    # Improved percent sign detection: match '%' after a digit and followed by whitespace or end-of-string
    r"(?<=\d)%(?=\s|$)", r"\bpercent\b",
    r"\b°c\b", r"\bdegc\b", r"\b°f\b"
]

# Pre-compile regexes for efficiency
UNIT_REGEXES = [re.compile(p) for p in UNIT_PATTERNS]

OUTCOME_MAP = {
    "improved": "positive",
    "successful": "positive",
    "pass": "positive",
    "positive": "positive",
    "degraded": "negative",
    "failed": "negative",
    "fail": "negative",
    "negative": "negative",
    "neutral": "neutral",
    "mixed": "neutral",
    "stable": "neutral",
    "unknown": "unknown",
}

SOURCE_WEIGHTS = {
    "reddit": 0.25,
    "forum": 0.35,
    "social_post": 0.35,
    "blog": 0.55,
    "news": 0.65,
    "industry_article": 0.75,
    "technical_report": 0.85,
    "research_paper": 0.9,
    "standard": 1.0,
    "code_standard": 1.0,
}

STRONG_RESULT_TERMS = [
    "improved", "enhanced", "higher", "reduced", "lower", "decreased",
    "failed", "collapse", "non-compliant", "complies", "meets", "worsened", "exacerbated"
]

MODERATE_CONTEXT_TERMS = [
    "measured", "tested", "evaluated", "simulated", "modeled", "validated",
    "due to", "caused by", "resulted from", "requirements", "standard", "specimens"
]


def has_unit_signal(s_l: str) -> bool:
    return any(p.search(s_l) for p in UNIT_REGEXES)


def has_number(s_l: str) -> bool:
    return bool(re.search(r"\b\d+(\.\d+)?\b", s_l))


def contains_any(s_l: str, phrases: List[str]) -> bool:
    return any(p in s_l for p in phrases)


def wordhit(s_l: str, phrase: str) -> bool:
    return bool(re.search(r"\b" + re.escape(phrase) + r"\b", s_l))


def list_hits(s_l: str, vocab: List[str]) -> List[str]:
    hits = []
    for v in vocab:
        if re.search(r"\b" + re.escape(v) + r"\b", s_l):
            hits.append(v)
    return hits


def normalize_outcome(outcome: Optional[str]) -> str:
    """Map lens-specific outcome words into analytics-friendly buckets."""
    key = str(outcome or "").strip().lower()
    if not key:
        return "unknown"
    return OUTCOME_MAP.get(key, "unknown")


def infer_context_strength(sentence: str, *, has_numbers: Optional[bool] = None, has_units: Optional[bool] = None) -> str:
    """Estimate whether the sentence is just a mention, measured, or strongly quantified."""
    s_l = sentence.lower()
    numbers = has_number(s_l) if has_numbers is None else has_numbers
    units = has_unit_signal(s_l) if has_units is None else has_units

    has_strong_terms = any(wordhit(s_l, term) for term in STRONG_RESULT_TERMS)
    has_context_terms = any(wordhit(s_l, term) for term in MODERATE_CONTEXT_TERMS)

    if (numbers and units) or (has_strong_terms and (numbers or units)):
        return "strong"
    if numbers or units or has_context_terms:
        return "moderate"
    return "weak"


def get_source_weight(source_type: Optional[str]) -> float:
    """Assign higher trust to more authoritative sources."""
    key = str(source_type or "research_paper").strip().lower()
    return SOURCE_WEIGHTS.get(key, SOURCE_WEIGHTS["research_paper"])


# ---------- Basic entity builder ----------
def make_entity(entity_type: str, name: str, variant: Optional[str], role: str) -> Dict:
    return {
        "entity_type": entity_type,
        "entity_name": name,
        "entity_variant": variant,
        "role": role,
    }


def dedupe_entities(entities: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for e in entities:
        entity_name = str(e["entity_name"]).lower()

        # Filter out junk entities
        if not entity_name or len(entity_name) < 2:
            continue  # Skip empty or single character entities

        if entity_name in {"]", "[", ")", "(", "{", "}", "-", "_", "=", "+", "*", "&", "^", "%", "$", "#", "@", "!", "~", "`"}:
            continue  # Skip punctuation-only entities

        if all(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in entity_name):
            continue  # Skip entities that are only punctuation/symbols

        if entity_name in {"indirect", "direct", "positive", "negative", "control", "test", "sample", "result", "data", "method", "analysis", "study", "research", "paper", "article", "report"}:
            continue  # Skip generic terms that aren't specific entities

        k = (e["entity_type"], entity_name, e.get("entity_variant") or "", e.get("role") or "")
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


@dataclass
class LensEvent:
    event_type: str
    outcome: str
    confidence: str
    tags: List[str] = field(default_factory=list)
    context_strength: str = "weak"
    source_weight: float = 0.9
    lens: Optional[str] = None
    raw_outcome: str = "unknown"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "lens": self.lens,
            "event_type": self.event_type,
            "outcome": self.outcome,
            "raw_outcome": self.raw_outcome,
            "confidence": self.confidence,
            "context_strength": self.context_strength,
            "source_weight": self.source_weight,
            "tags": list(self.tags),
        }


def build_lens_event(
    lens_name: str,
    event_type: str,
    raw_outcome: Optional[str],
    confidence: str,
    tags: List[str],
    sentence: str,
    source_type: str = "research_paper",
) -> LensEvent:
    """Create a product-ready lens event with normalized analytics fields."""
    s_l = sentence.lower()
    normalized_raw_outcome = (str(raw_outcome) if raw_outcome is not None else "").strip().lower()
    return LensEvent(
        event_type=event_type,
        outcome=normalize_outcome(raw_outcome),
        confidence=confidence,
        tags=tags,
        context_strength=infer_context_strength(
            sentence,
            has_numbers=has_number(s_l),
            has_units=has_unit_signal(s_l),
        ),
        source_weight=get_source_weight(source_type),
        lens=lens_name,
        raw_outcome=normalized_raw_outcome or "unknown",
    )
