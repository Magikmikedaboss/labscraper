import csv
from pathlib import Path

import pytest

from utils.export import reporting


def test_export_entities_csv_writes_overlay_scores_and_defaults(tmp_path):
    entities = [
        {
            "entity_id": "e1",
            "entity_name": "Entity One",
            "entity_type": "compound",
            "entity_variant": None,
        },
        "not-a-dict",
    ]
    entity_events = {"e1": ["ev1", "ev2"]}
    entity_scores = {
        "e1": {
            "ov1": {"score": 1.234, "bucket": "strong"},
        }
    }

    entities_file, filtered = reporting.export_entities_csv(
        entities=entities,
        entity_events=entity_events,
        entity_scores=entity_scores,
        overlay_ids=["ov1", "ov2"],
        domain_id="construction_science",
        output_path=tmp_path,
        should_suppress_entity_for_csv=lambda entity, _entity_events: False,
    )

    assert entities_file.exists()
    assert len(filtered) == 2

    with entities_file.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    row = rows[0]
    assert row["entity_name"] == "Entity One"
    assert row["event_count"] == "2"
    assert row["ov1_score"] == "1.23"
    assert row["ov1_bucket"] == "strong"
    assert row["ov2_score"] == ""
    assert row["ov2_bucket"] == "N/A"


def test_export_events_csv_formats_scores_and_defaults(tmp_path):
    events = [
        {
            "event_id": "ev1",
            "event_type": "failure",
            "stage": "pilot",
            "confidence": "high",
            "evidence_snippet": "x" * 250,
        },
        {
            "event_type": "success",
            "stage": "",
            "evidence_snippet": None,
        },
    ]
    event_overlay_scores = {"ev1": {"ov1": 1.5}}

    events_file = reporting.export_events_csv(
        events=events,
        event_overlay_scores=event_overlay_scores,
        overlay_ids=["ov1"],
        domain_id="construction_science",
        output_path=tmp_path,
    )

    with events_file.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 2
    assert rows[0]["event_id"] == "ev1"
    assert rows[0]["stage"] == "pilot"
    assert rows[0]["ov1_score"] == "+1.5"
    assert rows[0]["evidence_snippet"] == ("x" * 200) + "..."
    assert rows[1]["event_id"] == ""
    assert rows[1]["stage"] == ""
    assert rows[1]["confidence_original"] == "unknown"
    assert rows[1]["ov1_score"] == "+0.0"


def test_publish_latest_files_and_invalid_domain(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)

    entities_file = tmp_path / "entities.csv"
    entities_file.write_text("a,b\n1,2\n", encoding="utf-8")
    latest_entities, error = reporting.publish_latest_entities(entities_file, "construction_science")
    assert error is None
    assert latest_entities is not None
    assert latest_entities.exists()

    events_file = tmp_path / "events.csv"
    events_file.write_text("x,y\n3,4\n", encoding="utf-8")
    latest_events, error = reporting.publish_latest_events(events_file, "construction_science")
    assert error is None
    assert latest_events is not None
    assert latest_events.exists()

    def fail_unlink(*args, **kwargs):
        raise OSError("unlink failed")

    def fail_replace(*args, **kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "unlink", fail_unlink, raising=False)
    monkeypatch.setattr(reporting.os, "replace", fail_replace)

    with caplog.at_level("WARNING"):
        result, error = reporting._publish_latest_file(entities_file, tmp_path / "latest.csv")

    assert result is None
    assert isinstance(error, OSError)
    assert any("Failed to clean up temp file" in msg for msg in caplog.messages)

    with pytest.raises(ValueError):
        reporting.publish_latest_entities(entities_file, "../bad")


def test_write_dual_lens_report_handles_empty_overlays(tmp_path, caplog):
    report_file = tmp_path / "dual_lens_report.txt"

    with caplog.at_level("INFO"):
        reporting.write_dual_lens_report(
            report_file=report_file,
            domain_config="not-a-dict",
            overlay_ids=[],
            events=[],
            entities=[],
            filtered_entities=[],
            entity_scores={},
            entity_events={},
        )

    content = report_file.read_text(encoding="utf-8")
    assert "No bucket data available (no overlays configured)." in content
    assert any("domain_config is not a dict" in msg for msg in caplog.messages)
    assert any("No overlays configured" in msg for msg in caplog.messages)
