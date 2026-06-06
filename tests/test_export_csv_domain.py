import sqlite3
from pathlib import Path

import pytest

from utils import export_csv


def _init_minimal_export_db(db_path: Path):
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            CREATE TABLE entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT,
                entity_name TEXT,
                entity_variant TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE event_entities (
                entity_id TEXT,
                event_id TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE research_events (
                event_id TEXT PRIMARY KEY,
                research_domain TEXT,
                source_id TEXT
            )
            """
        )


def test_export_candidates_domain_aware_rejects_invalid_domain_id():
    with pytest.raises(ValueError):
        export_csv.export_candidates_domain_aware(domain_id="../bad")


def test_export_candidates_domain_aware_writes_domain_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "runs.sqlite"
    _init_minimal_export_db(db_path)

    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO entities VALUES (?, ?, ?, ?)", ("e1", "assay", "PCR", "v1"))
        con.execute("INSERT INTO research_events VALUES (?, ?, ?)", ("ev1", "construction_science", "s1"))
        con.execute("INSERT INTO event_entities VALUES (?, ?)", ("e1", "ev1"))

    monkeypatch.setattr(export_csv, "DB_PATH", db_path)
    monkeypatch.setattr(export_csv, "load_normalization_map", lambda: {})
    monkeypatch.setattr(export_csv, "load_overlay_aliases", lambda _domain_id: {})
    monkeypatch.setattr(export_csv, "normalize_entity", lambda entity, _norm, _aliases: entity)
    monkeypatch.setattr(export_csv, "get_entity_role", lambda _entity, _norm: "primary")
    monkeypatch.setattr(export_csv, "is_process_word", lambda _value: False)

    result = export_csv.export_candidates_domain_aware(domain_id="construction_science")

    assert ("assay", "PCR") in result
    assert result[("assay", "PCR")]["event_count"] == 1

    entities_path = tmp_path / "exports" / "latest" / "construction_science" / "entities.csv"
    assert entities_path.exists()
    content = entities_path.read_text(encoding="utf-8")
    assert "entity_name,entity_type,entity_variant,event_count" in content
    assert "PCR,assay,v1,1" in content


def test_export_candidates_domain_aware_logs_malformed_variant_split(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "runs.sqlite"
    _init_minimal_export_db(db_path)

    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO entities VALUES (?, ?, ?, ?)", ("e1", "compound", "Alpha", "  alpha  "))
        con.execute("INSERT INTO entities VALUES (?, ?, ?, ?)", ("e2", "compound", "Alpha", "beta  "))
        con.execute("INSERT INTO research_events VALUES (?, ?, ?)", ("ev1", "construction_science", "s1"))
        con.execute("INSERT INTO research_events VALUES (?, ?, ?)", ("ev2", "construction_science", "s2"))
        con.execute("INSERT INTO event_entities VALUES (?, ?)", ("e1", "ev1"))
        con.execute("INSERT INTO event_entities VALUES (?, ?)", ("e2", "ev2"))

    monkeypatch.setattr(export_csv, "DB_PATH", db_path)
    monkeypatch.setattr(export_csv, "load_normalization_map", lambda: {})
    monkeypatch.setattr(export_csv, "load_overlay_aliases", lambda _domain_id: {})
    monkeypatch.setattr(export_csv, "normalize_entity", lambda entity, _norm, _aliases: entity)
    monkeypatch.setattr(export_csv, "get_entity_role", lambda _entity, _norm: "primary")
    monkeypatch.setattr(export_csv, "is_process_word", lambda _value: False)

    with caplog.at_level("WARNING"):
        result = export_csv.export_candidates_domain_aware(domain_id="construction_science")

    assert ("compound", "Alpha") in result
    assert any("Malformed entity_variant split" in msg for msg in caplog.messages)


def test_export_candidates_domain_aware_without_domain_uses_default_query(tmp_path, monkeypatch):
    db_path = tmp_path / "runs.sqlite"
    _init_minimal_export_db(db_path)

    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO entities VALUES (?, ?, ?, ?)", ("e1", "target", "mTOR", "isoform A"))
        con.execute("INSERT INTO research_events VALUES (?, ?, ?)", ("ev1", "methods_tooling", "s1"))
        con.execute("INSERT INTO event_entities VALUES (?, ?)", ("e1", "ev1"))

    monkeypatch.setattr(export_csv, "DB_PATH", db_path)
    monkeypatch.setattr(export_csv, "load_normalization_map", lambda: {})
    monkeypatch.setattr(export_csv, "load_overlay_aliases", lambda _domain_id: {})
    monkeypatch.setattr(export_csv, "normalize_entity", lambda entity, _norm, _aliases: entity)
    monkeypatch.setattr(export_csv, "get_entity_role", lambda _entity, _norm: "primary")
    monkeypatch.setattr(export_csv, "is_process_word", lambda _value: False)

    result = export_csv.export_candidates_domain_aware(domain_id=None)

    assert ("target", "mTOR") in result
    assert result[("target", "mTOR")]["event_count"] == 1
    assert "isoform A" in result[("target", "mTOR")]["entity_variant"]
