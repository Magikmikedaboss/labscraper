import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import types
import pytest

from utils import (
    check_biohacking_compounds,
    check_compound_extraction,
    check_confidence,
    check_entity_types,
    check_longevity_compounds,
    check_recent_run,
    check_target_in_pdfs,
    check_neural_cells,
)


def _init_basic_entities_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.executescript(
            """
            CREATE TABLE entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT,
                entity_name TEXT
            );
            CREATE TABLE event_entities (
                entity_id TEXT,
                event_id TEXT
            );
            CREATE TABLE research_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT,
                stage TEXT,
                confidence TEXT,
                evidence_snippet TEXT
            );
            """
        )


def test_check_compound_extraction_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "runs" / "test_enhanced_seeds.sqlite"
    _init_basic_entities_db(db_path)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO entities(entity_id, entity_type, entity_name) VALUES (?, ?, ?)", ("e1", "compound", "metformin"))

    seeds_path = tmp_path / "seeds" / "base" / "compounds.txt"
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    seeds_path.write_text("metformin\nresveratrol\n", encoding="utf-8")

    check_compound_extraction.check_compound_extraction()
    output = capsys.readouterr().out
    assert "COMPOUND EXTRACTION ANALYSIS" in output
    assert "metformin" in output


def test_check_biohacking_compounds_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "output" / "biohacking_dual_lens.sqlite"
    _init_basic_entities_db(db_path)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO entities(entity_id, entity_type, entity_name) VALUES (?, ?, ?)", ("e1", "compound", "NMN"))
        con.execute("INSERT INTO event_entities(entity_id, event_id) VALUES (?, ?)", ("e1", "ev1"))

    check_biohacking_compounds.check_biohacking_compounds()
    output = capsys.readouterr().out
    assert "BIOHACKING SCRAPE - COMPOUND DETECTION RESULTS" in output
    assert "NMN" in output


def test_check_longevity_compounds_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    compounds_path = tmp_path / "seeds" / "base" / "life_sciences" / "compounds.txt"
    compounds_path.parent.mkdir(parents=True, exist_ok=True)
    compounds_path.write_text("nmn\nresveratrol\n", encoding="utf-8")

    check_longevity_compounds.check_longevity_compounds()
    output = capsys.readouterr().out
    assert "LONGEVITY COMPOUND CHECK" in output
    assert "nmn" in output.lower()


def test_check_recent_run_main_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    meta_path = tmp_path / "output" / "run_meta_neuroscience_cognition.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "engine_version": "v1",
                "domain_name": "neuroscience",
                "counts": {
                    "total_events": 1,
                    "total_entities": 1,
                    "primary_entities": 1,
                    "context_entities": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    result = check_recent_run.main()
    output = capsys.readouterr().out
    assert result is None
    assert "NEUROSCIENCE RUN INFORMATION" in output


def test_check_recent_run_missing_file_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    result = check_recent_run.main()
    output = capsys.readouterr().out
    assert result == 1
    assert "not found" in output


def test_check_recent_run_invalid_timestamp_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    meta_path = tmp_path / "output" / "run_meta_neuroscience_cognition.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps({"timestamp": "not-a-timestamp"}), encoding="utf-8")

    result = check_recent_run.main()
    output = capsys.readouterr().out
    assert result == 1
    assert "Invalid timestamp format" in output


def test_check_confidence_distribution_and_entity_types(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "output" / "peptide_intel.sqlite"
    _init_basic_entities_db(db_path)
    with sqlite3.connect(db_path) as con:
        con.execute("INSERT INTO entities(entity_id, entity_type, entity_name) VALUES (?, ?, ?)", ("e1", "compound", "X"))
        con.execute("INSERT INTO entities(entity_id, entity_type, entity_name) VALUES (?, ?, ?)", ("e2", "target", "Y"))
        con.execute(
            "INSERT INTO research_events(event_id, event_type, stage, confidence, evidence_snippet) VALUES (?, ?, ?, ?, ?)",
            ("ev1", "test", "preclinical", "high", "snippet"),
        )
        con.execute("INSERT INTO event_entities(entity_id, event_id) VALUES (?, ?)", ("e1", "ev1"))

    check_confidence.check_confidence_distribution()
    confidence_output = capsys.readouterr().out
    assert "Total events:" in confidence_output

    check_entity_types.main()
    entity_output = capsys.readouterr().out
    assert "ENTITY BREAKDOWN BY TYPE" in entity_output


def test_check_confidence_distribution_zero_total(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "output" / "peptide_intel.sqlite"
    _init_basic_entities_db(db_path)

    check_confidence.check_confidence_distribution()
    output = capsys.readouterr().out
    assert "0.0%" in output


def test_check_target_in_pdfs_main(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "paper.pdf").write_bytes(b"%PDF")

    class DummyPDF:
        def __init__(self):
            self.pages = [types.SimpleNamespace(extract_text=lambda: "MTOR and AMPK signals")]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(check_target_in_pdfs, "pdfplumber", types.SimpleNamespace(open=lambda _path: DummyPDF()))

    check_target_in_pdfs.main()
    output = capsys.readouterr().out
    assert "CHECKING FOR TARGETS IN PDFs" in output
    assert "MTOR" in output


def test_check_neural_cells_script_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    seeds_path = tmp_path / "seeds" / "neural_cells.json"
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    seeds_path.write_text(
        json.dumps({"neural_cells": ["neuron", "microglia", "astrocyte"]}),
        encoding="utf-8",
    )

    assert check_neural_cells.main() == 0
    output = capsys.readouterr().out
    assert "Total neural cells" in output
    assert "Found: neuron" in output


def test_check_neural_cells_script_missing_file_exits(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert check_neural_cells.main() == 1
    output = capsys.readouterr().out
    assert "not found" in output


def test_check_neural_cells_script_missing_key_exits(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    seeds_path = tmp_path / "seeds" / "neural_cells.json"
    seeds_path.parent.mkdir(parents=True, exist_ok=True)
    seeds_path.write_text(json.dumps({"wrong_key": []}), encoding="utf-8")

    assert check_neural_cells.main() == 1
    output = capsys.readouterr().out
    assert "Expected 'neural_cells' key" in output
