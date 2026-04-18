"""
Event classification rules and helpers for PDF scraping pipeline.
Includes: METHOD_TAGS, FAILURE_PHRASES, DECISION_PHRASES, OUTCOME_PHRASES, detect_method_tags, detect_failure_reason, detect_decision, detect_outcome, classify_event_type, evidence_strength, confidence_score, suggested_keep.
"""
from typing import List, Tuple, Any

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
    tags = []
    for tag, phrases in METHOD_TAGS.items():
        if any(p in sentence_l for p in phrases):
            tags.append(tag)
    return tags

def detect_failure_reason(sentence_l: str) -> str:
    for reason, phrases in FAILURE_PHRASES.items():
        if any(p in sentence_l for p in phrases):
            return reason
    return "unknown"

def detect_decision(sentence_l: str) -> Tuple[str, Any]:
    for decision, phrases in DECISION_PHRASES.items():
        if any(p in sentence_l for p in phrases):
            return decision, None
    return "unknown", None

def detect_outcome(sentence_l: str) -> str:
    for outcome in ["negative", "positive", "neutral"]:
        if any(p in sentence_l for p in OUTCOME_PHRASES[outcome]):
            return outcome
    return "unknown"

def classify_event_type(sentence_l: str, method_tags: List[str], failure_reason: str, decision_taken: str) -> str:
    s = sentence_l
    # 1. Regulatory
    if "nitrosamine" in method_tags or failure_reason == "regulatory":
        return "regulatory_risk"
    # 2. Toxicity
    if failure_reason == "toxicity_flag" or "toxic" in s:
        return "toxicity_flag"
    # 3. Stability issue or Degradation
    if failure_reason == "stability_failure":
        return "stability_issue"
    if any(k in s for k in ["degradation", "degraded", "corrosion", "rust", "oxidation", "deterioration", "decay", "weathering"]):
        return "degradation_event"
    # 4. Structural failure
    if any(k in s for k in ["crack", "cracking", "buckling", "delamination", "fracture", "rupture", "collapse", "shear failure", "yielding", "spalling", "failure mode"]):
        return "structural_failure"
    # 5. Environmental stress
    if any(k in s for k in ["temperature", "thermal", "moisture", "humidity", "freeze", "thaw", "uv", "solar", "environmental stress", "exposure"]):
        return "environmental_stress"
    # 6. Load event
    if any(k in s for k in ["impact", "load", "loading", "stress", "strain", "pressure", "force", "torsion", "bending", "compression", "tension"]):
        return "load_event"
    # 7. Fatigue
    if "fatigue" in s:
        return "fatigue_event"    # 8. Efficacy
    if failure_reason == "no_activity" or any(k in s for k in ["activity", "efficacy", "potent", "ic50", "ec50"]):
        return "efficacy_result"
    # 9. Manufacturing constraint
    if failure_reason == "scalability" or any(k in s for k in ["manufacturing", "scale-up", "yield"]):
        return "manufacturing_constraint"
    # 10. Cost tradeoff
    if method_tags:
        if any(k in s for k in ["cost-intensive", "expensive", "time-consuming", "fast", "cost-effective"]):
            return "cost_tradeoff"
        return "method_evaluation"
    # 11. Decision point
    if decision_taken != "unknown":
        return "decision_point"
    # 12. Fallback
    return "other"

def evidence_strength(sentence_l: str) -> str:
    if any(k in sentence_l for k in ["we conclude", "demonstrate", "significant", "robust", "strong"]):
        return "strong"
    if any(k in sentence_l for k in ["suggest", "may", "might", "could", "trend"]):
        return "weak"
    return "moderate"

def confidence_score(has_entity: bool, method_tags: List[str], failure_reason: str, decision_taken: str, has_measurements: bool, sentence_l: str = "", HIGH_CONF_THRESHOLD: int = 6, MED_CONF_THRESHOLD: int = 3) -> str:
    score = 0
    if has_entity:
        score += 2
    if method_tags:
        score += 1
    if failure_reason != "unknown":
        score += 2
    if decision_taken != "unknown":
        score += 1
    if has_measurements:
        score += 2
    high_signal_terms = [
        'lc-ms', 'mass spectrometry', 'in vivo', 'in vitro', 'clinical',
        'sequence', 'residues', 'ic50', 'ec50', 'half-life',
        'degraded', 'stable', 'potent', 'toxic', 'efficacy',
        'optimized', 'modified', 'abandoned', 'continued'
    ]
    signal_count = sum(1 for term in high_signal_terms if term in sentence_l)
    if signal_count >= 3:
        score += 2
    elif signal_count >= 2:
        score += 1
    if score >= HIGH_CONF_THRESHOLD:
        return "high"
    elif score >= MED_CONF_THRESHOLD:
        return "med"
    else:
        return "low"

def suggested_keep(conf: str, event_type: str, failure_reason: str, decision_taken: str, tags: List[str]) -> int:
    if conf in ("med", "high"):
        return 1
    if event_type not in ("other",) and (failure_reason != "unknown" or decision_taken != "unknown" or tags):
        return 1
    return 0
