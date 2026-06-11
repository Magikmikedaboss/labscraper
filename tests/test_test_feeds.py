import pytest
import json
from utils.validators import validate_feed_config, validate_file_path, ValidationError
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

def test_validate_feed_config_allows_collector_metadata():
    config = {
        "feeds": [
            {
                "name": "Collector Feed",
                "url": "http://example.com/rss",
                "domain": "construction_science",
                "source_kind": "collector",
                "collector_mode": "html_archive",
                "same_domain_only": False,
                "max_pages": 7,
            }
        ]
    }

    loaded = validate_feed_config(config)

    feed = loaded["feeds"][0]
    assert feed["source_kind"] == "collector"
    assert feed["collector_mode"] == "html_archive"
    assert feed["same_domain_only"] is False
    assert feed["max_pages"] == 7

# Add more tests for probe_feed, error handling, and save-working logic as needed

def test_probe_feed_success(monkeypatch):
    # Mock feedparser.parse to return a valid feed with entries and a PDF link
    monkeypatch.setattr(
        "utils.feed_utils.parse_feed",
        lambda *args, **kwargs: {
            'entries': [{
                'summary': 'See https://example.com/test.pdf',
                'title': 'Test Entry',
                'content': [],
                'links': [{'href': 'https://example.com/test.pdf'}],
            }],
            'feed': {'title': 'Test Feed'},
        },
    )
    result = probe_feed("http://example.com/rss", "Test Feed")
    assert result['success'] is True
    assert result['entries'] == 1
    assert result['pdfs'] == 1
    assert result['title'] == 'Test Feed'

def test_probe_feed_http_error(monkeypatch):
    # Mock feedparser.parse to return a feed with HTTP error status
    monkeypatch.setattr(
        "utils.feed_utils.parse_feed",
        lambda *args, **kwargs: {'entries': [], 'feed': {'title': 'Test Feed'}, 'status': 404},
    )
    result = probe_feed("http://example.com/rss", "Test Feed")
    assert result['success'] is False
    assert 'error' in result
    assert '404' in result['error']

def test_probe_feed_exception(monkeypatch):
    # Mock feedparser.parse to raise an exception
    def raise_exc(*args, **kwargs):
        raise Exception("network error")
    monkeypatch.setattr("utils.feed_utils.parse_feed", raise_exc)
    result = probe_feed("http://example.com/rss", "Test Feed")
    assert result['success'] is False
    assert 'network error' in result['error']

def test_save_working_logic(tmp_path, monkeypatch):
    from tools import test_feeds
    save_path = tmp_path / "feeds.json"
    save_path.write_text(
        json.dumps(
            {
                "feeds": [
                    {
                        "name": "Collector Feed",
                        "url": "http://example.com/rss",
                        "domain": "construction_science",
                        "source_kind": "collector",
                        "collector_mode": "html_archive",
                        "same_domain_only": False,
                        "max_pages": 7,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    # Patch probe_feed to avoid network I/O
    monkeypatch.setattr(test_feeds, "probe_feed", lambda *a, **k: {'success': True, 'url': 'mock'})
    # Provide clean CLI args so argparse won’t see pytest’s argv
    argv = ["--config", str(save_path), "--save-working"]
    expected_written = save_path.with_name(save_path.stem + "_working.json")
    test_feeds.main(argv)
    saved_config = json.loads(expected_written.read_text(encoding="utf-8"))
    saved_feed = saved_config["feeds"][0]
    assert saved_feed["source_kind"] == "collector"
    assert saved_feed["collector_mode"] == "html_archive"
    assert saved_feed["same_domain_only"] is False
    assert saved_feed["max_pages"] == 7


def test_main_handles_pdf_list_feed(tmp_path, monkeypatch, capsys):
    from tools import test_feeds

    config_path = tmp_path / "feeds.json"
    config_path.write_text(
        json.dumps(
            {
                "feeds": [
                    {
                        "name": "FEMA Building Science Publications",
                        "domain": "construction_science",
                        "source_kind": "pdf_list",
                        "pdf_urls": [
                            "https://example.com/a.pdf",
                            "https://example.com/b.pdf",
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    test_feeds.main(["--config", str(config_path), "--save-working"])

    output = capsys.readouterr().out
    assert "PDF list source" in output
    saved_config = json.loads(config_path.with_name("feeds_working.json").read_text(encoding="utf-8"))
    saved_feed = saved_config["feeds"][0]
    assert saved_feed["source_kind"] == "pdf_list"
    assert saved_feed["pdf_urls"] == ["https://example.com/a.pdf", "https://example.com/b.pdf"]

def test_probe_feed_with_invalid_config(monkeypatch):
    # probe_feed should return failure when config is missing 'url'
    result = probe_feed(None, "Test Feed")
    assert result['success'] is False
    assert 'error' in result and bool(result['error'])
    assert "url" in result['error'].lower()
