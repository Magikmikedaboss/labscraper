"""
Event classification rules and helpers for PDF scraping pipeline.
Includes: METHOD_TAGS, FAILURE_PHRASES, DECISION_PHRASES, OUTCOME_PHRASES, detect_method_tags, detect_failure_reason, detect_decision, detect_outcome, classify_event_type, evidence_strength, confidence_score, suggested_keep.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Any
@dataclass
class ConfidenceInput:
    has_entity: bool = False
    method_tags: list[str] = field(default_factory=list)
    failure_reason: str = ""
    decision_taken: str = ""
    has_measurements: bool = False
    sentence_l: str = ""

@dataclass
class ConfidenceConfig:
    HIGH_CONF_THRESHOLD: int = 6
    MED_CONF_THRESHOLD: int = 3
    high_signal_terms: list = field(default_factory=lambda: [
        'lc-ms', 'mass spectrometry', 'in vivo', 'in vitro', 'clinical',
        'sequence', 'residues', 'ic50', 'ec50', 'half-life',
        'degraded', 'stable', 'potent', 'toxic', 'efficacy',
        'optimized', 'modified', 'abandoned', 'continued'
    ])
# Canonical keyword sets for event type classification (no duplicates, context-specific where needed)
DEGRADATION_KEYWORDS = [
    "degradation", "degraded", "corrosion", "rust", "oxidation", "deterioration", "decay", "weathering", "aging",
    "short half-life", "poor stability", "unstable", "instability"  # Only chemical/temporal instability
]
STRUCTURAL_KEYWORDS = [
    "crack", "cracking", "buckling", "delamination", "fracture", "rupture", "collapse", "shear failure", "yielding",
    "spalling", "failure mode", "microcrack", "macrocrack", "brittle fracture", "ductile fracture", "plastic hinge",
    # Only structural instability (use word-boundary or phrase)
    "structural instability"
]
ENVIRONMENTAL_KEYWORDS = [
    "temperature", "thermal", "moisture", "humidity", "freeze", "thaw", "uv", "solar", "environmental stress", "exposure",
    "weather", "climate", "precipitation", "snow", "hail", "thermal shock"
]
LOAD_KEYWORDS = [
    "impact", "load", "loading", "stress", "strain", "pressure", "force", "torsion", "bending", "compression", "tension",
    "modulus", "stiffness", "ductility", "hardness", "strength", "yield strength", "ultimate strength", "elasticity", "plasticity"
]
FATIGUE_KEYWORDS = ["fatigue", "creep", "shrinkage"]
EFFICACY_KEYWORDS = ["activity", "efficacy", "potent", "ic50", "ec50", "performance", "effectiveness", "output", "result"]
MANUFACTURING_KEYWORDS = ["manufacturing", "scale-up", "yield", "production", "fabrication", "assembly", "costly to produce", "process", "costly"]
COST_TRADEOFF_KEYWORDS = ["cost-intensive", "expensive", "time-consuming", "fast", "cost-effective", "affordable", "cheap", "efficient", "resource-intensive"]
HAZARD_KEYWORDS = [
    "flood", "seismic", "earthquake", "corrosion", "erosion", "vibration", "overload", "fire hazard", "chemical attack", "abrasion",
    "freeze-thaw", "alkali-silica reaction", "subsidence", "settlement", "liquefaction", "tsunami", "landslide", "storm", "hurricane", "typhoon", "cyclone"
]



METHOD_TAGS = {
    "lc-ms/ms": ["lc-ms/ms", "lc ms/ms", "lc-ms", "mass spectrometry", "ms/ms"],
    "fluorescent": ["fluorescent", "fluorescence", "fluorophore", "label"],
    "serum": ["serum", "plasma", "biological fluids"],
    "incubation": ["incubation", "long incubation"],
    "nitrosamine": ["nitrosamine", "nitrosamines"],
    "gmp": ["gmp", "good manufacturing practice"],
}

FAILURE_PHRASES = {
    "stability_failure": ["rapidly degraded", "degraded", "unstable", "poor stability", "short half-life"],
    "no_activity": ["no significant", "no measurable", "did not show", "no activity", "inactive"],
    "toxicity_flag": ["cytotoxic", "toxicity", "cell death"],
    "reproducibility": [
        "not reproducible", "poor reproducibility", "lack of reproducibility", "irreproducible", "failed reproducibility"
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
        "no significant", "no measurable", "inactive", "excluded", "not pursued", "did not",
        "failed to", "no improvement", "worsened", "decreased", "declined", "degradation",
        "toxic", "toxicity", "adverse"
    ],
    "positive": [
        "improved", "increased", "enhanced", "more stable", "longer half-life", "better",
        "higher", "greater", "successful", "showed activity", "demonstrated", "significant"
    ],
    "neutral": ["moderate", "marginal", "partial", "mixed", "limited", "trend"],
}

def detect_method_tags(sentence_l: str) -> List[str]:
    # Normalize input to lowercase string for robust matching
    norm = sentence_l.lower().strip() if isinstance(sentence_l, str) else ""
    tags = []
    for tag, phrases in METHOD_TAGS.items():
        for p in phrases:
            if re.fullmatch(r"\w+", p):
                # Match not surrounded by word characters (handles punctuation/end)
                pat = re.compile(rf"(?<!\w){re.escape(p)}(?!\w)", re.IGNORECASE)
                if pat.search(norm):                    tags.append(tag)
            else:
                if p.lower() in norm:
                    tags.append(tag)
    # Remove duplicates, preserve order
    return list(dict.fromkeys(tags))

def detect_failure_reason(sentence_l: str) -> str:
    norm = sentence_l.lower().strip() if isinstance(sentence_l, str) else ""
    for reason, phrases in FAILURE_PHRASES.items():
        for p in phrases:
            if re.fullmatch(r"\w+", p):
                pat = re.compile(rf"(?<!\w){re.escape(p)}(?!\w)", re.IGNORECASE)
                if pat.search(norm):
                    return reason
            else:
                if p.lower() in norm:
                    return reason
    return "unknown"

def detect_decision(sentence_l: str) -> Tuple[str, Any]:
    norm = sentence_l.lower().strip() if isinstance(sentence_l, str) else ""
    for decision, phrases in DECISION_PHRASES.items():
        for p in phrases:
            if re.fullmatch(r"\w+", p):
                pat = re.compile(rf"(?<!\w){re.escape(p)}(?!\w)", re.IGNORECASE)
                if pat.search(norm):
                    return decision, None
            else:
                if p.lower() in norm:
                    return decision, None
    return "unknown", None

def detect_outcome(sentence_l: str) -> str:
    norm = sentence_l.lower().strip() if isinstance(sentence_l, str) else ""
    for outcome in ["negative", "positive", "neutral"]:
        for p in OUTCOME_PHRASES[outcome]:
            if re.fullmatch(r"\w+", p):
                pat = re.compile(rf"(?<!\w){re.escape(p)}(?!\w)", re.IGNORECASE)
                if pat.search(norm):
                    return outcome
            else:
                if p.lower() in norm:
                    return outcome
    return "unknown"

def classify_event_type(sentence_l: str, method_tags: List[str], failure_reason: str, decision_taken: str) -> str:
    """
    Classifies event type from sentence and context.
    Priority order (first match wins):
      1. regulatory_risk
      2. toxicity_flag
      3. stability_issue
      4. degradation_event (chemical/temporal instability, not structural)
      5. structural_failure (structural instability, cracks, etc.)
      6. environmental_stress
      7. load_event
      8. fatigue_event
      9. efficacy_result
     10. manufacturing_constraint
     11. cost_tradeoff/method_evaluation
     12. hazard_event
     13. decision_point
     14. other
    Keyword sets are canonical and disambiguated; e.g., "instability" is only degradation unless "structural instability" is present.
    """
    s = sentence_l.lower().strip() if isinstance(sentence_l, str) else ""
    # 1. Regulatory
    if "nitrosamine" in method_tags or failure_reason == "regulatory":
        return "regulatory_risk"
    # 2. Toxicity
    if failure_reason == "toxicity_flag" or any(k in s for k in ["toxic", "toxicity", "cytotoxic"]):
        return "toxicity_flag"
    # 3. Stability issue
    if failure_reason == "stability_failure":
        return "stability_issue"
    # 4. Degradation (chemical/temporal instability, not structural)
    # Only match "instability" if not part of "structural instability"
    if any(k in s for k in DEGRADATION_KEYWORDS) and "structural instability" not in s:
        return "degradation_event"
    # 5. Structural failure (structural instability, cracks, etc.)
    if any(k in s for k in STRUCTURAL_KEYWORDS):
        # 6. Environmental stress
        return "structural_failure"
    if any(k in s for k in ENVIRONMENTAL_KEYWORDS):
        return "environmental_stress"
    # 7. Load event
    if any(k in s for k in LOAD_KEYWORDS):
        return "load_event"
    # 8. Fatigue
    if any(k in s for k in FATIGUE_KEYWORDS):
        return "fatigue_event"
    # 9. Efficacy
    if failure_reason == "no_activity" or any(k in s for k in EFFICACY_KEYWORDS):
        return "efficacy_result"
    # 10. Manufacturing constraint
    if failure_reason == "scalability" or any(k in s for k in MANUFACTURING_KEYWORDS):
        return "manufacturing_constraint"
    # 11. Cost tradeoff/method evaluation
    if method_tags:
        if any(k in s for k in COST_TRADEOFF_KEYWORDS):
            return "cost_tradeoff"
        return "method_evaluation"
    # 12. Hazard event
    if any(k in s for k in HAZARD_KEYWORDS):
        return "hazard_event"
    # 13. Decision point
    if decision_taken != "unknown":
        return "decision_point"
    # 14. Fallback
    return "other"

def evidence_strength(sentence_l: str) -> str:
    if any(k in sentence_l for k in ["we conclude", "demonstrate", "significant", "robust", "strong"]):
        return "strong"
    if any(k in sentence_l for k in ["suggest", "may", "might", "could", "trend"]):
        return "weak"
    return "moderate"

def confidence_score(conf_input: ConfidenceInput, config: Optional[ConfidenceConfig] = None) -> str:
    if config is None:
        config = ConfidenceConfig()
    score = 0
    if conf_input.has_entity:
        score += 2
    if conf_input.method_tags:
        score += 1
    if conf_input.failure_reason != "unknown":
        score += 2
    if conf_input.decision_taken != "unknown":
        score += 1
    if conf_input.has_measurements:
        score += 2
    signal_count = sum(1 for term in config.high_signal_terms if term in conf_input.sentence_l)
    if signal_count >= 3:
        score += 2
    elif signal_count >= 2:
        score += 1
    if score >= config.HIGH_CONF_THRESHOLD:
        return "high"
    elif score >= config.MED_CONF_THRESHOLD:
        return "med"
    else:
        return "low"

def suggested_keep(conf: str, event_type: str, failure_reason: str, decision_taken: str, tags: List[str]) -> int:
    if conf in ("med", "high"):
        return 1
    if event_type not in ("other",) and (failure_reason != "unknown" or decision_taken != "unknown" or tags):
        return 1
    return 0
