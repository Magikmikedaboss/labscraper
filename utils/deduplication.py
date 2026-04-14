"""
Deduplication helpers for PDF scraping pipeline.
Includes: normalize_event_key.
"""
from utils.common import sha16

def normalize_event_key(event_type: str, entities: list, page: int, snippet: str) -> str:
    """Create key for deduplication"""
    entity_str = "|".join(sorted(e['entity_name'] for e in entities))
    snippet_hash = sha16(snippet[:100])
    return f"{event_type}|{entity_str}|{page}|{snippet_hash}"
