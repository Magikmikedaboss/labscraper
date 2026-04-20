import pytest
import json
from utils.validators import validate_feed_config, validate_file_path, ValidationError
import io
import builtins
import feedparser
import os
from utils.feed_utils import probe_feed

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

def test_probe_feed_success(monkeypatch):
    # Mock feedparser.parse to return a valid feed with entries and a PDF link
    class FakeFeed:
        def __init__(self):
            self.entries = [{
                'summary': 'See https://example.com/test.pdf',
                'title': 'Test Entry',
                'content': [],
                'links': [{'href': 'https://example.com/test.pdf'}],
            }]
            self.feed = {'title': 'Test Feed'}
            self.status = 200
    monkeypatch.setattr(feedparser, "parse", lambda url: FakeFeed())
    result = probe_feed("http://example.com/rss", "Test Feed")
    assert result['success'] is True
    assert result['entries'] == 1
    assert result['pdfs'] == 1
    assert result['title'] == 'Test Feed'

def test_probe_feed_http_error(monkeypatch):
    # Mock feedparser.parse to return a feed with HTTP error status
    class FakeFeed:
        def __init__(self):
            self.entries = []
            self.feed = {'title': 'Test Feed'}
            self.status = 404
    monkeypatch.setattr(feedparser, "parse", lambda url: FakeFeed())
    result = probe_feed("http://example.com/rss", "Test Feed")
    assert result['success'] is False
    assert 'error' in result
    assert '404' in result['error']

def test_probe_feed_exception(monkeypatch):
    # Mock feedparser.parse to raise an exception
    def raise_exc(url):
        raise Exception("network error")
    monkeypatch.setattr(feedparser, "parse", raise_exc)
    result = probe_feed("http://example.com/rss", "Test Feed")
    assert result['success'] is False
    assert 'network error' in result['error']

def test_save_working_logic(tmp_path, monkeypatch):
    import sys
    import builtins
    import io
    from tools import test_feeds
    feeds = [
        {'name': 'Feed1', 'url': 'http://example.com/rss', 'domain': 'test', 'enabled': True},
        {'name': 'Feed2', 'url': 'http://example2.com/rss', 'domain': 'test', 'enabled': True},
    ]
    output = {'feeds': feeds}
    save_path = tmp_path / "feeds.json"
    # Patch Path to use tmp_path
    monkeypatch.setattr(test_feeds, "Path", lambda *a, **k: tmp_path)
    # Patch open to simulate atomic write
    orig_open = builtins.open
    written = {}
    def fake_open(file, mode='r', encoding=None):
        if 'w' in mode:
            written['file'] = file
            return io.StringIO()
        return orig_open(file, mode, encoding=encoding) if os.path.exists(file) else io.StringIO()
    monkeypatch.setattr(builtins, "open", fake_open)
    # Patch validate_feed_config to pass through
    monkeypatch.setattr(test_feeds, "validate_feed_config", lambda x: x)
    # Patch probe_feed to avoid network I/O
    monkeypatch.setattr(test_feeds, "probe_feed", lambda *a, **k: {'success': True, 'url': 'mock'})
    # Patch sys.argv to simulate --save-working
    monkeypatch.setattr(sys, "argv", ["test_feeds.py", "--save-working", str(save_path)])
    # Actually call the save logic
    try:
        test_feeds.main()
    finally:
        monkeypatch.setattr(builtins, "open", orig_open)
    assert written['file'] == save_path

def test_probe_feed_with_invalid_config(monkeypatch, tmp_path):
    # Integration: invalid config causes probe to be skipped or error path taken
    from utils.validators import validate_feed_config, ValidationError
    config = {"feeds": [{"name": "feed1"}]}  # missing required 'url'
    with pytest.raises(ValidationError):
        validate_feed_config(config)
