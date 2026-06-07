import csv
import sqlite3
from pathlib import Path
import pytest

from utils import cleanup_obsolete
from utils import check_db_schema
from utils import check_output_files
from utils import domain_enforcement
from utils import entity_extractor
from utils import init_construction_db
from utils import init_db
from utils import init_test_db
from utils import show_all_exports
from utils import view_pattern_export


def test_check_db_schema_prints_tables(tmp_path, capsys):
    db_path = tmp_path / "schema.sqlite"
    with sqlite3.connect(db_path) as con:
        con.execute("CREATE TABLE demo (id INTEGER, name TEXT)")

    check_db_schema.check_db_schema(str(db_path))
    output = capsys.readouterr().out
    assert "Tables:" in output
    assert "demo" in output


def test_check_db_schema_main_usage_and_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["check_db_schema.py"])
    assert check_db_schema.main() == 1
    err_output = capsys.readouterr().err
    assert "Usage:" in err_output

    bad_path = tmp_path / "missing_parent" / "missing.sqlite"
    monkeypatch.setattr("sys.argv", ["check_db_schema.py", str(bad_path)])
    assert check_db_schema.main() == 1
    err_output = capsys.readouterr().err
    assert "Error:" in err_output


def test_check_output_files_script_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "a.txt").write_text("x", encoding="utf-8")
    (output_dir / "b.txt").write_text("xx", encoding="utf-8")

    assert check_output_files.main() == 0
    output = capsys.readouterr().out
    assert "OUTPUT FOLDER FILES" in output
    assert "Total files:" in output


def test_show_all_exports_script_all_found(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "candidates_primary_v4.csv",
        "events_export_v4.csv",
        "pattern_intelligence_export.csv",
    ]:
        (output_dir / name).write_text("h\n", encoding="utf-8")

    assert show_all_exports.main() == 0
    output = capsys.readouterr().out
    assert "All 3 CSV exports are current" in output


def test_show_all_exports_script_some_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "events_export_v4.csv").write_text("h\n", encoding="utf-8")

    assert show_all_exports.main() == 0
    output = capsys.readouterr().out
    assert "Missing" in output
    assert "Found 1 file(s)" in output


def test_view_pattern_export_paths(tmp_path, monkeypatch, capsys):
    missing_path = tmp_path / "missing.csv"
    monkeypatch.setattr(view_pattern_export, "OUTPUT_FILE", missing_path)
    view_pattern_export.view_export()
    assert "Export file not found" in capsys.readouterr().out

    bad_cols = tmp_path / "bad_cols.csv"
    bad_cols.write_text("entity_name,entity_type\nfoo,bar\n", encoding="utf-8")
    monkeypatch.setattr(view_pattern_export, "OUTPUT_FILE", bad_cols)
    view_pattern_export.view_export()
    assert "missing required columns" in capsys.readouterr().out

    good_csv = tmp_path / "good.csv"
    with good_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "pattern_type",
                "entity_name",
                "entity_type",
                "health_score",
                "event_count",
                "positive_signals",
                "neutral_signals",
                "negative_signals",
                "replication_signals",
                "interpretation",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "pattern_type": "convergence",
                "entity_name": "Entity A",
                "entity_type": "compound",
                "health_score": "85",
                "event_count": "4",
                "positive_signals": "2",
                "neutral_signals": "1",
                "negative_signals": "0",
                "replication_signals": "1",
                "interpretation": "Strong momentum",
            }
        )
        writer.writerow(
            {
                "pattern_type": "abandonment",
                "entity_name": "Entity B",
                "entity_type": "target",
                "health_score": "10",
                "event_count": "1",
                "positive_signals": "0",
                "neutral_signals": "0",
                "negative_signals": "2",
                "replication_signals": "0",
                "interpretation": "Declining attention",
            }
        )

    monkeypatch.setattr(view_pattern_export, "OUTPUT_FILE", good_csv)
    view_pattern_export.view_export()
    output = capsys.readouterr().out
    assert "PATTERN INTELLIGENCE EXPORT VIEWER" in output
    assert "Top 15 Entities" in output


def test_view_pattern_export_empty_and_invalid_values(tmp_path, monkeypatch, capsys):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text(
        "pattern_type,entity_name,entity_type,health_score,event_count,positive_signals,neutral_signals,negative_signals,replication_signals\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(view_pattern_export, "OUTPUT_FILE", empty_csv)
    view_pattern_export.view_export()
    assert "Export file is empty" in capsys.readouterr().out

    weird_csv = tmp_path / "weird.csv"
    weird_csv.write_text(
        "pattern_type,entity_name,entity_type,health_score,event_count,positive_signals,neutral_signals,negative_signals,replication_signals,interpretation\n"
        "fragmentation,Odd Entity,target,not-an-int,2,NaN,bad,??,oops,No interpretation\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(view_pattern_export, "OUTPUT_FILE", weird_csv)
    view_pattern_export.view_export()
    output = capsys.readouterr().out
    assert "0.0%" in output


def test_cleanup_obsolete_dry_run_and_remove(tmp_path, monkeypatch):
    old_file = tmp_path / "old.txt"
    old_file.write_text("legacy", encoding="utf-8")

    monkeypatch.setattr(cleanup_obsolete, "BASE_DIR", tmp_path)
    monkeypatch.setattr(cleanup_obsolete, "OBSOLETE_FILES", ["old.txt"])
    monkeypatch.setattr(cleanup_obsolete, "OBSOLETE_OUTPUTS", [])

    cleanup_obsolete.cleanup(dry_run=True)
    assert old_file.exists()

    cleanup_obsolete.cleanup(dry_run=False)
    assert not old_file.exists()


def test_entity_extractor_seed_loading_and_scoring(tmp_path):
    seeds_dir = tmp_path / "seeds"
    seeds_dir.mkdir(parents=True, exist_ok=True)
    (seeds_dir / "assays.json").write_text('{"assays": [{"name": "ELISA"}], "metrics": ["IC50"]}', encoding="utf-8")
    (seeds_dir / "pathways.json").write_text('{"pathways": ["mTOR"]}', encoding="utf-8")
    (seeds_dir / "indications.json").write_text('{"indications": ["cancer"]}', encoding="utf-8")

    ontology_dir = seeds_dir / "base" / "bio"
    ontology_dir.mkdir(parents=True, exist_ok=True)
    (ontology_dir / "targets.txt").write_text("AKT\nPI3K\n", encoding="utf-8")

    loaded = entity_extractor.load_seeds(str(seeds_dir))
    assert "json_seeds" in loaded
    assert "ontology_seeds" in loaded
    assert "targets" in loaded["ontology_seeds"]["bio"]

    text = "ELISA measured IC50 and mTOR response in cancer"
    entities = entity_extractor.extract_entities(text, loaded)
    assert entities
    label, score = entity_extractor.score_event_confidence(entities, text, loaded)
    assert label in {"med", "high"}
    assert 0 <= score <= 1


def test_domain_enforcement_paths(capsys):
    assert domain_enforcement.is_entity_type_allowed_for_domain("compound", "unknown_domain")
    assert domain_enforcement.is_entity_type_allowed_for_domain("material", "construction_science")
    assert not domain_enforcement.is_entity_type_allowed_for_domain("peptide", "construction_science")

    filtered = domain_enforcement.filter_entities_for_domain(
        [{"entity_type": "material"}, {"entity_type": "peptide"}],
        "construction_science",
    )
    assert len(filtered) == 1
    output = capsys.readouterr().out
    assert "Filtering out entity type" in output

    unknown_passthrough = domain_enforcement.filter_entities_for_domain([
        {"entity_type": "anything"}
    ], "unknown_domain")
    assert len(unknown_passthrough) == 1

    contaminated = domain_enforcement.get_contaminated_entity_types("construction_science")
    assert "peptide" in contaminated
    assert "material" not in contaminated


def test_init_scripts_create_databases(tmp_path, monkeypatch):
    con = init_db.get_connection_with_foreign_keys(str(tmp_path / "fk.sqlite"))
    try:
        fk_val = con.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        con.close()
    assert fk_val == 1

    init_db.main(str(tmp_path / "main.sqlite"))
    assert (tmp_path / "main.sqlite").exists()

    init_test_db.init_test_db(str(tmp_path / "test.sqlite"))
    assert (tmp_path / "test.sqlite").exists()

    monkeypatch.chdir(tmp_path)
    init_construction_db.main()
    assert (tmp_path / "output" / "peptide_intel_construction.sqlite").exists()


def test_init_script_guardrails_raise_for_canonical_db(tmp_path, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    fake_root = tmp_path / "fake_project"
    fake_root.mkdir()
    (fake_root / "db").mkdir()
    (fake_root / "schema.sql").write_text((project_root / "schema.sql").read_text(encoding="utf-8"), encoding="utf-8")

    canonical = fake_root / "db" / "runs.sqlite"
    monkeypatch.setattr(init_db, "__file__", str(fake_root / "utils" / "init_db.py"), raising=False)

    with pytest.raises(RuntimeError):
        init_db.main(str(canonical))

    init_db.main(str(canonical), force=True)
    assert canonical.exists()
