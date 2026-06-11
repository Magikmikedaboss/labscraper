from __future__ import annotations

from types import SimpleNamespace


def test_summarize_rss_feed(monkeypatch):
    from tools import audit_feeds

    monkeypatch.setattr(
        audit_feeds,
        "parse_feed",
        lambda *args, **kwargs: {
            "entries": [
                {
                    "title": "First item",
                    "link": "https://example.com/article-1",
                    "summary": "See https://example.com/paper-1.pdf",
                    "links": [{"href": "https://example.com/paper-1.pdf"}],
                },
                {
                    "title": "Second item",
                    "link": "https://example.com/article-2",
                    "summary": "No PDF here",
                    "links": [],
                },
            ],
            "feed": {"title": "Example Feed"},
        },
    )
    monkeypatch.setattr(
        audit_feeds,
        "get_pdf_links_from_entry",
        lambda entry: ["https://example.com/paper-1.pdf"] if entry.get("title") == "First item" else [],
    )
    monkeypatch.setattr(audit_feeds, "download_pdf", lambda *args, **kwargs: object())
    monkeypatch.setattr(audit_feeds, "is_valid_pdf", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        audit_feeds,
        "scan_pdf",
        lambda *args, **kwargs: SimpleNamespace(keep_skip_review="keep", detected_domain="construction_science"),
    )

    row = audit_feeds._summarize_rss_feed(
        {"name": "Example Feed", "url": "https://example.com/rss", "domain": "construction_science", "enabled": True}
    )

    assert row["feed_name"] == "Example Feed"
    assert row["source_kind"] == "rss"
    assert row["entries_found"] == 2
    assert row["pdf_links_found"] == 1
    assert row["pdfs_downloaded"] == 1
    assert row["keep"] == 1
    assert row["first_10_discovered_urls"][0] == "https://example.com/article-1"
    assert row["first_10_pdf_urls"][0] == "https://example.com/paper-1.pdf"