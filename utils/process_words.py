"""
Shared module for process words demotion logic.
Used by export_csv_v4_professional.py and export_csv_v5_domain_aware.py
"""

# Process words that should be tags, not primary assay entities
# These are generic lab terms that don't represent specific research assays
PROCESS_WORDS_TO_DEMOTE = {
    # Sample prep & processing
    "quantification", "quantitation", "chromatography", "purification",
    "calibration", "validation", "optimization", "quality control",

    # Generic measurement terms
    "affinity", "binding affinity", "affinity measurement", "affinity assay",

    # Mobile phase & standards
    "internal standard", "mobile phase", "gradient", "elution",

    # Generic detection
    "detection", "analysis", "measurement", "determination"
}

def is_process_word(entity_name: str) -> bool:
    """Check if entity is a process word that should be demoted to tag"""
    return entity_name.lower() in PROCESS_WORDS_TO_DEMOTE
