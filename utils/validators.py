"""Input validation utilities for the peptide scraper project"""

from pathlib import Path
from typing import Any, Union, Dict, Optional
import re


class ValidationError(Exception):
    """Validation error for input validation failures"""
    pass


def validate_directory(path: Union[str, Path], must_exist: bool = True) -> Path:
    """
    Validate directory path
    
    Args:
        path: Directory path to validate
        must_exist: If True, directory must exist
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If validation fails
    """
    p = Path(path)
    
    if must_exist and not p.exists():
        raise ValidationError(f"Directory not found: {path}")
    
    if p.exists() and not p.is_dir():
        raise ValidationError(f"Not a directory: {path}")
    
    return p


def validate_database(path: Union[str, Path], must_exist: bool = False) -> Path:
    """Validate SQLite database path."""
    p = Path(path)

    if p.suffix.lower() not in ['.db', '.sqlite', '.sqlite3']:
        raise ValidationError(f"Invalid database extension: {p.suffix or '(missing extension)'}")

    if must_exist and not p.exists():
        raise ValidationError(f"Database not found: {path}")

    if p.exists() and not p.is_file():
        raise ValidationError(f"Not a file: {path}")

    parent = p.parent
    if not parent.exists():
        raise ValidationError(f"Database directory not found: {parent}")

    return p


def ensure_database_dir(path: Union[str, Path]) -> Path:
    """Create the parent directory for a database path if needed."""
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValidationError(f"Failed to create database directory '{p.parent}': {e}") from e
    return p


def validate_feed_url(url: str) -> str:
    """Validate RSS feed URL"""
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string")
    
    # Basic URL pattern validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise ValidationError(f"Invalid feed URL format: {url}")
    
    return url


def validate_file_path(path: Union[str, Path], must_exist: bool = True) -> Path:
    """Validate file path"""
    p = Path(path)
    
    if must_exist and not p.exists():
        raise ValidationError(f"File not found: {path}")
    
    if p.exists() and not p.is_file():
        raise ValidationError(f"Not a file: {path}")
    
    return p


def validate_feed_entry(feed: Dict[str, Any], index: Optional[int] = None) -> Dict[str, Any]:
    """Validate and normalize a single RSS feed configuration entry."""
    prefix = f"Feed #{index}: " if index is not None else ""

    if not isinstance(feed, dict):
        raise ValidationError(f"{prefix}Feed entry must be an object")


    required_fields = ("name", "url")
    missing = [field for field in required_fields if field not in feed]
    if missing:
        raise ValidationError(f"{prefix}Missing required field(s): {', '.join(missing)}")

    empty = [field for field in required_fields if str(feed.get(field, "")).strip() == ""]
    if empty:
        raise ValidationError(f"{prefix}Empty value for field(s): {', '.join(empty)}")

    validated = {
        "name": str(feed["name"]).strip(),
        "url": validate_feed_url(str(feed["url"]).strip()),
        "enabled": bool(feed.get("enabled", True)),
    }

    if feed.get("domain"):
        validated["domain"] = validate_domain_name(str(feed["domain"]).strip())

    for optional_key in ("keywords", "notes"):
        if optional_key in feed:
            value = feed[optional_key]
            feed_name = feed.get('name', f'<unknown#{index}>' if index is not None else '<unknown>')
            if optional_key == "keywords":
                # Accept only list/tuple of strings
                if not isinstance(value, (list, tuple)):
                    msg = f"{prefix}Feed '{feed_name}' has invalid type for 'keywords': {type(value).__name__}"
                    raise ValidationError(msg)
                if not all(isinstance(x, str) for x in value):
                    bad_types = [type(x).__name__ for x in value if not isinstance(x, str)]
                    msg = f"{prefix}Feed '{feed_name}' has non-string elements in 'keywords': {bad_types}"
                    raise ValidationError(msg)
                validated[optional_key] = list(value)
            elif optional_key == "notes":
                # Accept only str or None
                if value is not None and not isinstance(value, str):
                    msg = f"{prefix}Feed '{feed_name}' has invalid type for 'notes': {type(value).__name__}"
                    raise ValidationError(msg)
                validated[optional_key] = value

    return validated



def validate_feed_config(config: Any) -> Dict[str, Any]:
    """Validate the structure of an RSS feed configuration payload."""
    if not isinstance(config, dict):
        raise ValidationError("Feed config must be a JSON object")

    feeds = config.get("feeds", [])
    if feeds is None:
        feeds = []

    if not isinstance(feeds, list):
        raise ValidationError("Feed config field 'feeds' must be a list")

    validated_config = config.copy()
    validated_config["feeds"] = [
        validate_feed_entry(feed, index=i)
        for i, feed in enumerate(feeds, start=1)
    ]
    return validated_config


def validate_input_pdfs_directory(path: Union[str, Path]) -> Path:
    """Validate input PDFs directory"""
    p = validate_directory(path, must_exist=True)
    
    # Check if directory contains PDF files
    pdf_files = list(p.glob("*.pdf"))
    if not pdf_files:
        raise ValidationError(f"No PDF files found in directory: {path}")
    
    return p


def validate_output_path(path: Union[str, Path]) -> Path:
    """Validate output file path"""
    p = Path(path)
    
    # Check parent directory exists or can be created
    parent = p.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValidationError(f"Cannot create output directory: {e}")
    
    return p


def validate_domain_name(domain: str) -> str:
    """Validate domain name"""
    if not domain or not isinstance(domain, str):
        raise ValidationError("Domain name must be a non-empty string")
    
    # Check for valid characters (alphanumeric, underscore, hyphen)
    if not re.match(r'^[a-zA-Z0-9_-]+$', domain):
        raise ValidationError(f"Invalid domain name format: {domain}")
    
    return domain.lower()


def validate_positive_integer(value: Union[int, str], name: str = "value") -> int:
    """Validate positive integer"""
    try:
        int_value = int(value)
    except (ValueError, TypeError) as err:
        raise ValidationError(f"{name} must be an integer") from err
    
    if int_value <= 0:
        raise ValidationError(f"{name} must be positive")
    
    return int_value


def validate_percentage(value: Union[float, int, str], name: str = "percentage") -> float:
    """Validate percentage value (0.0 to 1.0)"""
    try:
        float_value = float(value)
    except (ValueError, TypeError) as err:
        raise ValidationError(f"{name} must be a number") from err
    
    if not 0.0 <= float_value <= 1.0:
        raise ValidationError(f"{name} must be between 0.0 and 1.0")
    
    return float_value


def validate_search_terms(terms: Union[str, list, tuple]) -> list:
    """Validate search terms"""
    if isinstance(terms, str):
        terms = [terms]
    elif not isinstance(terms, (list, tuple)):
        raise ValidationError("Search terms must be a string, list, or tuple")
    
    validated_terms = []
    for term in terms:
        if not isinstance(term, str) or not term.strip():
            raise ValidationError("All search terms must be non-empty strings")
        validated_terms.append(term.strip().lower())
    
    return validated_terms


def validate_batch_size(size: Union[int, str]) -> int:
    """Validate batch size for processing"""
    size_int = validate_positive_integer(size, "Batch size")
    if size_int > 1000:
        raise ValidationError("Batch size too large (max 1000)")
    return size_int


def validate_memory_limit(limit: Union[str, int]) -> int:
    """Validate memory limit in MB"""
    if isinstance(limit, str):
        # Handle string formats like "512MB", "1GB", "1.5GB" with regex
        limit = limit.strip().upper()
        
        # Pattern to match numbers with optional decimal and unit suffix
        pattern = r'^(\d+(?:\.\d+)?)\s*(MB|GB|G)?\s*$'
        match = re.match(pattern, limit)
        
        if not match:
            raise ValidationError("Invalid memory limit format")
        
        value_str, unit = match.groups()
        
        try:
            value = float(value_str)
        except ValueError as err:
            raise ValidationError("Invalid memory limit value") from err
        
        # Convert to MB
        if unit in ['GB', 'G']:
            value *= 1000
        
        limit_int = int(value)
    else:
        limit_int = validate_positive_integer(limit, "Memory limit")
    
    if limit_int < 100:
        raise ValidationError("Memory limit too small (min 100MB)")
    if limit_int > 16000:
        raise ValidationError("Memory limit too large (max 16000MB)")
    
    return limit_int
