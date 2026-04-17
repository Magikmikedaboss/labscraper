"""
Shared utilities for CSV export modules
- safe_confidence_boost: Safe confidence promotion rule
- count_entities_by_role: Count primary and context entities with process word demotion
- write_run_meta: Write run metadata for reproducibility
"""



# Import required modules


def safe_confidence_boost(entities_str: str, current_conf: str, domain_id: str = None) -> str:
    """
    Safe confidence promotion rule:
    Promote to HIGH if event has:
    - (domain-relevant entities) AND
    - assay AND
    - model context (in vivo/in vitro/human/rat/plasma/serum)
    
    This is objective, not subjective.
    """
    # Normalize confidence to known values (handle synonyms and unexpected values)
    conf_normalized = current_conf.lower().strip() if current_conf else "low"
    conf_map = {
        "high": "high",
        "med": "med",
        "medium": "med",
        "low": "low",
        "": "low",
        "none": "low"
    }
    conf_normalized = conf_map.get(conf_normalized, "other")

    if conf_normalized == "high":
        return "high"  # Already high

    if not entities_str:
        return conf_normalized
"""
This file has been refactored. All logic is now in:
  - confidence_utils.py
  - entity_utils.py
  - reporting_utils.py
Import from those modules instead.
"""