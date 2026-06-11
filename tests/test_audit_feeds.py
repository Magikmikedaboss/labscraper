from __future__ import annotations

from types import SimpleNamespace


def _triage_result(**kwargs):
    return SimpleNamespace(**kwargs)


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
        lambda entry, source_domain="": ["https://example.com/paper-1.pdf"] if entry.get("title") == "First item" else [],
    )
    monkeypatch.setattr(audit_feeds, "download_pdf", lambda *args, **kwargs: object())
    monkeypatch.setattr(audit_feeds, "is_valid_pdf", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        audit_feeds,
        "scan_pdf",
        lambda *args, **kwargs: SimpleNamespace(keep_skip_review="keep", detected_domain="construction_science"),
    )

    row = audit_feeds._summarize_rss_feed(
        {"name": "Example Feed", "url": "https://example.com/rss", "domain": "construction_science", "enabled": True, "trusted_source": True}
    )

    assert row["feed_name"] == "Example Feed"
    assert row["source_kind"] == "rss"
    assert row["entries_found"] == 2
    assert row["pdf_links_found"] == 1
    assert row["pdfs_downloaded"] == 1
    assert row["keep"] == 1
    assert row["first_10_discovered_urls"][0] == "https://example.com/article-1"
    assert row["first_10_pdf_urls"][0] == "https://example.com/paper-1.pdf"


def test_summarize_rss_feed_surfaces_promotion_fields(monkeypatch):
    from tools import audit_feeds

    monkeypatch.setattr(
        audit_feeds,
        "parse_feed",
        lambda *args, **kwargs: {
            "entries": [
                {
                    "title": "Promoted item",
                    "link": "https://example.com/article-1",
                    "summary": "See https://example.com/paper-1.pdf",
                    "links": [{"href": "https://example.com/paper-1.pdf"}],
                }
            ],
            "feed": {"title": "Example Feed"},
        },
    )
    monkeypatch.setattr(audit_feeds, "get_pdf_links_from_entry", lambda entry, source_domain="": ["https://example.com/paper-1.pdf"])
    monkeypatch.setattr(audit_feeds, "download_pdf", lambda *args, **kwargs: object())
    monkeypatch.setattr(audit_feeds, "is_valid_pdf", lambda *args, **kwargs: True)
    monkeypatch.setattr(audit_feeds, "_score_construction_review_lenses", lambda *args, **kwargs: {"building_physics": 12})
    monkeypatch.setattr(
        audit_feeds,
        "_promotion_decision_from_lens_counts",
        lambda lens_counts: (True, "building_physics hits=12 >= 3"),
    )
    monkeypatch.setattr(
        audit_feeds,
        "scan_pdf",
        lambda *args, **kwargs: _triage_result(
            keep_skip_review="review",
            triage_decision="review",
            detected_domain="construction_science",
        ),
    )

    row = audit_feeds._summarize_rss_feed(
        {"name": "Example Feed", "url": "https://example.com/rss", "domain": "construction_science", "enabled": True, "trusted_source": True}
    )

    assert row["pdfs_downloaded"] == 1
    assert row["pdfs_accepted"] == 1
    assert row["triage_decision"] == {"review": 1}
    assert row["lens_promoted"] == 1
    assert row["promotion_reason"] == {"building_physics hits=12 >= 3": 1}
    assert row["final_decision"] == {"keep": 1}