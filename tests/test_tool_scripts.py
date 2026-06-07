"""Tests for command-line tooling entry points."""

import json
import sys


import tools.inspect_db as inspect_db_module
import tools.test_feeds as test_feeds_module
from tools.test_feeds import default_feeds


def test_test_feeds_main_uses_validated_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "feeds.json"
    config_path.write_text(
        json.dumps(
            {
                "feeds": [
                    {
                        "name": "Example Feed",
                        "url": "https://example.com/feed.xml",
                        "domain": "construction_science",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    calls = []
    def fake_probe_feed(url, name, check_keywords=None):
        calls.append((url, name, check_keywords))
        return {"success": True, "pdfs": 1}
    monkeypatch.setattr(
        test_feeds_module,
        "probe_feed",
        fake_probe_feed,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["test_feeds.py", "--config", str(config_path), "--keywords", "concrete", "--save-working", "--default-domain", "construction_science"],
    )

    test_feeds_module.main()

    assert calls == [("https://example.com/feed.xml", "Example Feed", ["concrete"])]
    saved_config = json.loads((tmp_path / "feeds_working.json").read_text(encoding="utf-8"))
    assert saved_config["feeds"][0]["url"] == "https://example.com/feed.xml"
    assert saved_config["feeds"][0]["domain"] == "construction_science"


def test_test_feeds_main_falls_back_on_invalid_config(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "feeds.json"
    config_path.write_text(json.dumps({"feeds": {"bad": "structure"}}), encoding="utf-8")

    calls = []
    def fake_probe_feed(url, name, check_keywords=None):
        calls.append((url, name, check_keywords))
        return {"success": True, "pdfs": 0}
    monkeypatch.setattr(
        test_feeds_module,
        "probe_feed",
        fake_probe_feed,
    )
    monkeypatch.setattr(sys, "argv", ["test_feeds.py", "--config", str(config_path)])

    test_feeds_module.main()
    out = capsys.readouterr().out

    assert "Validation error" in out
    expected_len = len(default_feeds)
    assert len(calls) == expected_len


def test_inspect_db_main_invokes_helpers(monkeypatch):
    calls = []

    class DummyConnection:
        def close(self):
            calls.append("close")

    dummy_conn = DummyConnection()

    monkeypatch.setattr(
        inspect_db_module,
        "inspect_database",
        lambda db, detailed=False: calls.append(("inspect", db, detailed)),
    )
    def fake_connect(db):
        calls.append(("connect", db))
        return dummy_conn
    monkeypatch.setattr(
        inspect_db_module,
        "connect_db",
        fake_connect,
    )
    monkeypatch.setattr(inspect_db_module, "show_pdf_cache", lambda: calls.append("cache"))
    import utils.db_utils as db_utils
    monkeypatch.setattr(db_utils, "show_recent_events", lambda conn, count: calls.append(("events", count)))
    monkeypatch.setattr(db_utils, "show_top_sources", lambda conn, count: calls.append(("sources", count)))
    monkeypatch.setattr(db_utils, "get_entity_distribution", lambda conn: calls.append("entities"))
    monkeypatch.setattr(db_utils, "get_event_type_distribution", lambda conn: calls.append("event_types"))
    monkeypatch.setattr(db_utils, "get_domain_distribution", lambda conn: calls.append("domains"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inspect_db.py",
            "--db",
            "db/test.sqlite",
            "--detailed",
            "--events",
            "2",
            "--sources",
            "3",
            "--cache",
        ],
    )

    inspect_db_module.main()

    assert ("inspect", "db/test.sqlite", True) in calls
    assert ("connect", "db/test.sqlite") in calls
    assert ("events", 2) in calls
    assert ("sources", 3) in calls
    assert "entities" in calls
    assert "event_types" in calls
    assert "domains" in calls
    assert "cache" in calls
    assert "close" in calls
