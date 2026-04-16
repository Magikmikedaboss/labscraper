import pytest
import json
from utils.validators import validate_feed_config, validate_file_path, ValidationError

# Test for tools/test_feeds.py coverage (lines 40–57, 51–55, 92–93, 95)
def test_validate_feed_config_valid(tmp_path):
    config = {"feeds": [{"url": "http://example.com/rss", "name": "Example"}]}
    path = tmp_path / "feeds.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f)
    validated_path = validate_file_path(path)
    with open(validated_path, encoding="utf-8") as f:
        loaded = validate_feed_config(json.load(f))
    assert loaded["feeds"][0]["url"] == "http://example.com/rss"

def test_validate_feed_config_invalid(tmp_path):
    # Write structurally valid but semantically invalid JSON (missing 'url' field)
    config = {"feeds": [{"name": "feed1"}]}  # missing required 'url'
    path = tmp_path / "feeds.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f)
    with open(path, encoding="utf-8") as f:
        loaded = json.load(f)
    with pytest.raises(ValidationError, match="Missing required field"):
        validate_feed_config(loaded)

# Add more tests for probe_feed, error handling, and save-working logic as needed
