# Failure Analysis Lens v1
# Extracts failure modes, triggers, causality, and related entities from construction science text.

LENS_ID = "failure_analysis_v1"

TARGET_ENTITIES = [
    "failure_mode",
    "failure_driver",
    "component",
    "system",
    "evidence_snippet",
    "load_value",
    "strength_value"
]

KEYWORDS = [
    # Failure modes
    "cracking", "buckling", "corrosion", "fatigue", "spalling", "delamination", "creep", "settlement",
    # Triggers
    "overload", "poor detailing", "water intrusion", "thermal cycling", "chloride ingress", "freeze-thaw",
    # Causality
    "due to", "caused by", "attributed to", "root cause"
]

OUTPUT_TYPES = [
    "failure_mode",
    "failure_driver",
    "component",
    "system",
    "evidence_snippet",
    "load_value",
    "strength_value"
]
