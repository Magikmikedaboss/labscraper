from typing import Optional
import re

KNOWN_PEPTIDES = {
    "ETELCALCETIDE",
    "PLECANATIDE",
    "TERIPARATIDE",
    "OCTREOTIDE",
    "LANREOTIDE",
    "PASIREOTIDE",
    "SOMATOSTATIN",
}

# Minimum number of linked events required to keep peptide rows in CSV exports.
PEPTIDE_EVENT_THRESHOLD = 2

def is_valid_export_peptide(name: str) -> bool:
    """Filter obvious OCR/noise artifacts from peptide exports."""
    token = (name or "").strip()
    if not token:
        return False

    token_upper = token.upper()

    if re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]{8,100}", token_upper):
        return True

    return token_upper in KNOWN_PEPTIDES

def should_skip_entity(
    entity_type: str,
    canonical_name: str,
    role: str,
) -> bool:
    """Drop context-only entities and noisy peptides from ranking exports."""
    if role == "context":
        return True

    if entity_type == "peptide" and not is_valid_export_peptide(canonical_name):
        return True

    return False

def should_suppress_entity_for_csv(entity: dict, entity_events: Optional[dict] = None) -> bool:
    """Suppress very weak peptide rows in final CSV exports."""
    entity_type = entity.get("entity_type")
    entity_id = entity.get("entity_id")
    if entity_type != "peptide" or not entity_id:
        return False
    if entity_events is None:
        entity_events = {}
    return len(entity_events.get(entity_id, [])) < PEPTIDE_EVENT_THRESHOLD
