"""
Deduplication helpers for PDF scraping pipeline.
Includes: normalize_event_key.
"""

from typing import List, Optional

from utils.common import sha256_hex

def normalize_event_key(event_type: str, entities: Optional[List], page: int, snippet: Optional[str]) -> str:
    """Create a deduplication key using the full snippet hash to reduce collisions."""
    # Guard: treat None as empty list for entities
    if entities is None:
        entities = []
    # Defensive: skip None items and only use dict-like objects
    def safe_entity_name(e):
        if isinstance(e, dict):
            return e.get('entity_name', '')
        return ''

    entity_names = sorted(name for name in (safe_entity_name(e) for e in entities) if name)
    entity_str = "|".join(entity_names)

    snippet_safe = snippet if snippet is not None else ""
    snippet_hash = sha256_hex(snippet_safe)
    return f"{event_type}|{entity_str}|{page}|{snippet_hash}"
