"""
Shared module for process words demotion logic.
Used by export_csv_v4_professional.py and export_csv_v5_domain_aware.py
"""

# Process words that should be tags, not primary assay entities
# These are generic terms that don't represent specific research assays
# Domain-appropriate for construction science
PROCESS_WORDS_TO_DEMOTE = {
    # Sample prep & processing
    "quantification", "quantitation", "purification",
    "calibration", "validation", "optimization", "quality control",

    # Generic measurement terms
    "measurement", "determination", "analysis",

    # Construction-specific generic terms
    "testing", "evaluation", "assessment", "inspection",
    "monitoring", "surveying",
    # Administrative terms
    "report", "documentation", "record", "log",
    "procedure", "protocol", "method", "technique"
}

def is_process_word(entity_name: str) -> bool:
    """Check if entity is a process word that should be demoted to tag"""
    return entity_name.lower() in PROCESS_WORDS_TO_DEMOTE
