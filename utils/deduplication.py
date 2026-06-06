"""
Deduplication helpers for PDF scraping pipeline.
Includes: normalize_event_key.
"""

from typing import List, Optional

from utils.common import sha16


SNIPPET_HASH_PREFIX_LEN = 100  # Limit snippet hash to 100 chars for performance; 100 chars is sufficient for uniqueness in deduplication

def normalize_event_key(event_type: str, entities: Optional[List], page: int, snippet: Optional[str]) -> str:
    """Create key for deduplication"""
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
    snippet_hash = sha16(snippet_safe[:SNIPPET_HASH_PREFIX_LEN])  # Truncate for performance and sufficient uniqueness
    return f"{event_type}|{entity_str}|{page}|{snippet_hash}"
