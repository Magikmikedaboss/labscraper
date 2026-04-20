"""
Deduplication helpers for PDF scraping pipeline.
Includes: normalize_event_key.
"""

from typing import Optional, List
from utils.common import sha16

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
    names = []
    for e in entities:
        if not e:
            continue
        name = safe_entity_name(e)
        if name:
            names.append(name)
    entity_str = "|".join(sorted(names))
    # Guard: treat None as empty string for snippet
    snippet_safe = snippet if snippet is not None else ""
    snippet_hash = sha16(snippet_safe[:100])
    return f"{event_type}|{entity_str}|{page}|{snippet_hash}"
