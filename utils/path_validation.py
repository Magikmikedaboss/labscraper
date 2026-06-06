import os
import re
from pathlib import Path


_DOMAIN_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_domain_id(domain_id: str) -> str:
    """Validate a domain id for safe single-segment path usage."""
    if not isinstance(domain_id, str) or not domain_id.strip():
        raise ValueError("domain_id must be a non-empty string")
    if ".." in domain_id:
        raise ValueError("Invalid domain_id: parent path traversal is not allowed")
    if any(sep in domain_id for sep in ("/", "\\")):
        raise ValueError("Invalid domain_id: path separators are not allowed")
    p = Path(domain_id)
    if p.is_absolute() or len(p.parts) != 1:
        raise ValueError("Invalid domain_id: must be a single safe path segment")
    if os.path.isabs(domain_id):
        raise ValueError("Invalid domain_id: absolute paths are not allowed")
    if not _DOMAIN_ID_RE.match(domain_id):
        raise ValueError("Invalid domain_id: only letters, numbers, underscore, and hyphen are allowed")
    return domain_id
