from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import scrape_abstracts


class _FakeFeed:
    entries = [{"id": "entry-1", "link": "https://example.com/entry-1", "title": "Entry 1"}]


def test_main_logs_entry_failure_and_continues(monkeypatch, tmp_path, capsys):
    feeds_config = {
        "feeds": [
            {
                "name": "example",
                "url": "https://example.com/feed.xml",
                "enabled": True,
                "domain": "construction_science",
            }
        ]
    }

    monkeypatch.setattr(scrape_abstracts, "validate_file_path", lambda path, must_exist=False: Path(path))
    monkeypatch.setattr(scrape_abstracts, "validate_database", lambda path, must_exist=False: Path(path))
    monkeypatch.setattr(scrape_abstracts, "validate_domain_name", lambda domain: domain)
    monkeypatch.setattr(scrape_abstracts, "load_feeds_config", lambda path: feeds_config)
    monkeypatch.setattr(scrape_abstracts, "ensure_database_dir", lambda path: Path(path))
    monkeypatch.setattr(scrape_abstracts, "ensure_db_schema", lambda path: None)
    monkeypatch.setattr(scrape_abstracts.feedparser, "parse", lambda url: _FakeFeed())

    def fake_process_feed_entry(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(scrape_abstracts, "process_feed_entry", fake_process_feed_entry)

    logged = {}

    def fake_exception(message, *args):
        logged["message"] = message % args

    monkeypatch.setattr(scrape_abstracts.logger, "exception", fake_exception)
    monkeypatch.setattr(
        scrape_abstracts,
        "argparse",
        SimpleNamespace(
            ArgumentParser=scrape_abstracts.argparse.ArgumentParser,
        ),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "scrape_abstracts.py",
            "--feeds-config",
            str(tmp_path / "feeds.json"),
            "--db-path",
            str(tmp_path / "runs.sqlite"),
            "--domain",
            "construction_science",
        ],
    )

    scrape_abstracts.main()

    captured = capsys.readouterr()
    assert "HYBRID PROCESSING COMPLETE" in captured.out
    assert "Failed processing feed entry 'entry-1' from https://example.com/feed.xml" in logged["message"]
