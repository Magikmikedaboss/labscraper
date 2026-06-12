import sqlite3
import hashlib
from pathlib import Path
from utils import scrape_pdfs_parallel
from utils.source_triage import TriagedSource
import types
from unittest.mock import MagicMock
import pytest

# Patch for multiprocessing and pdfplumber

class DummyPDF:
    def __init__(self, pages):
        self.pages = pages
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class DummyPage:
    def __init__(self, text):
        self._text = text
    def extract_text(self):
        return self._text

def test__connect(tmp_path):
    db = tmp_path / "test.sqlite"
    con = scrape_pdfs_parallel._connect(db)
    try:
        assert isinstance(con, sqlite3.Connection)
    finally:
        con.close()


def test_sha64_shim_uses_underlying_impl(monkeypatch):
    monkeypatch.setattr(scrape_pdfs_parallel, "_sha64", lambda value: f"hashed:{value}")
    assert scrape_pdfs_parallel.sha64("abc") == "hashed:abc"


def test__has_signal_detects_phrases():
    failure_phrase = next(iter(next(iter(scrape_pdfs_parallel.FAILURE_PHRASES.values()))))
    assert scrape_pdfs_parallel._has_signal(f"prefix {failure_phrase} suffix")
    assert not scrape_pdfs_parallel._has_signal("totally unrelated sentence")


def test__sha256_file(tmp_path):
    file_path = tmp_path / "data.bin"
    payload = b"abc123" * 1000
    file_path.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()
    assert scrape_pdfs_parallel._sha256_file(file_path, chunk_size=64) == expected

def test__db_has_all_tables(tmp_path):
    db = tmp_path / "test.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE sources (id INTEGER)")
    con.execute("CREATE TABLE documents (id INTEGER)")
    con.execute("CREATE TABLE chunks (id INTEGER)")
    con.execute("CREATE TABLE entities (id INTEGER)")
    con.execute("CREATE TABLE research_events (id INTEGER)")
    con.execute("CREATE TABLE event_entities (id INTEGER)")
    con.execute("CREATE TABLE tags (id INTEGER)")
    con.execute("CREATE TABLE event_tags (id INTEGER)")
    con.execute("CREATE TABLE quantitative_measurements (id INTEGER)")
    con.execute("CREATE TABLE entity_relationships (id INTEGER)")
    con.commit()
    con.close()
    assert scrape_pdfs_parallel._db_has_all_tables(db)


# The failure path for _ensure_db_schema is tested elsewhere. This redundant test is removed.

def test_process_single_pdf(monkeypatch, tmp_path):
    """
    Smoke/integration-orchestration test for process_single_pdf.
    Ensures that the function orchestrates its helpers and DB logic as expected.
    """
    # Ensure at least one sentence and signal
    monkeypatch.setattr(scrape_pdfs_parallel, "chunk_sentences", lambda text: ["Concrete wall assembly failed under load."])
    monkeypatch.setattr(scrape_pdfs_parallel, "_has_signal", lambda s: True)
    dummy_pdf = DummyPDF([DummyPage("test text")])
    monkeypatch.setattr(scrape_pdfs_parallel, "pdfplumber", types.SimpleNamespace(open=lambda *a, **k: dummy_pdf))
    monkeypatch.setattr(scrape_pdfs_parallel, "_connect", lambda db: sqlite3.connect(db))
    monkeypatch.setattr(scrape_pdfs_parallel, "sha64", lambda s: "hash")
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_metadata", lambda *a, **k: {})
    # Use MagicMock for key helpers
    upsert_source = MagicMock(return_value=1)
    insert_document = MagicMock(return_value=1)
    insert_chunk = MagicMock(return_value=1)
    insert_event = MagicMock(return_value=1)
    upsert_entity = MagicMock(return_value=1)
    monkeypatch.setattr(scrape_pdfs_parallel, "upsert_source", upsert_source)
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_document", insert_document)
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_chunk", insert_chunk)
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_event", insert_event)
    monkeypatch.setattr(scrape_pdfs_parallel, "upsert_entity", upsert_entity)
    # Other mocks as before
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_method_tags", lambda s: ["tag"])
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_failure_reason", lambda s: "fail")
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_decision", lambda s: ("decision", "driver"))
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_outcome", lambda s: "outcome")
    monkeypatch.setattr(scrape_pdfs_parallel, "guess_stage", lambda s: "stage")
    monkeypatch.setattr(scrape_pdfs_parallel, "classify_event_type", lambda *a, **k: "type")
    monkeypatch.setattr(scrape_pdfs_parallel, "evidence_strength", lambda s: "strong")
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_entities", lambda s, d: [{"entity_type": "material", "entity_name": "concrete", "role": "primary"}])
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_quantitative_data", lambda s: [1])
    monkeypatch.setattr(scrape_pdfs_parallel, "confidence_score", lambda *a, **k: "med")
    monkeypatch.setattr(scrape_pdfs_parallel, "normalize_event_key", lambda *a, **k: "key")
    monkeypatch.setattr(scrape_pdfs_parallel, "ConfidenceInput", lambda **kwargs: kwargs)
    monkeypatch.setattr(scrape_pdfs_parallel, "link_event_tag", lambda *a, **k: None)
    monkeypatch.setattr(scrape_pdfs_parallel, "link_event_entity", lambda *a, **k: None)
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_measurement", lambda *a, **k: None)
    # Create a dummy PDF file so Path.exists() and stat() work
    pdf_path = tmp_path / "f.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%EOF")
    db_path = tmp_path / "db.sqlite"
    db_path.touch()
    job = (str(pdf_path), "domain", str(db_path))
    result = scrape_pdfs_parallel.process_single_pdf(job)
    assert result[2] is True
    # Assert key helpers were called
    upsert_source.assert_called()
    insert_document.assert_called()
    insert_chunk.assert_called()
    insert_event.assert_called()
    upsert_entity.assert_called()


def test_process_single_pdf_uses_stable_source_id_for_reprocessed_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(scrape_pdfs_parallel, "chunk_sentences", lambda text: ["Concrete wall assembly failed under load."])
    monkeypatch.setattr(scrape_pdfs_parallel, "_has_signal", lambda s: True)
    dummy_pdf = DummyPDF([DummyPage("test text")])
    monkeypatch.setattr(scrape_pdfs_parallel, "pdfplumber", types.SimpleNamespace(open=lambda *a, **k: dummy_pdf))
    monkeypatch.setattr(scrape_pdfs_parallel, "_connect", lambda db: sqlite3.connect(db))
    monkeypatch.setattr(scrape_pdfs_parallel, "sha64", lambda s: f"hashed:{s}")
    monkeypatch.setattr(
        scrape_pdfs_parallel,
        "extract_metadata",
        lambda *a, **k: {
            "doi": "10.1234/example",
            "title": "Reprocessed Paper",
            "authors": "A. Author",
            "year": 2024,
        },
    )
    upsert_source = MagicMock(side_effect=["sid-1", "sid-1"])
    monkeypatch.setattr(scrape_pdfs_parallel, "upsert_source", upsert_source)
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_document", MagicMock(return_value=1))
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_chunk", MagicMock(return_value=1))
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_event", MagicMock(return_value=1))
    monkeypatch.setattr(scrape_pdfs_parallel, "upsert_entity", MagicMock(return_value=1))
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_method_tags", lambda s: ["tag"])
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_failure_reason", lambda s: "fail")
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_decision", lambda s: ("decision", "driver"))
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_outcome", lambda s: "outcome")
    monkeypatch.setattr(scrape_pdfs_parallel, "guess_stage", lambda s: "stage")
    monkeypatch.setattr(scrape_pdfs_parallel, "classify_event_type", lambda *a, **k: "type")
    monkeypatch.setattr(scrape_pdfs_parallel, "evidence_strength", lambda s: "strong")
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_entities", lambda s, d: [{"entity_type": "material", "entity_name": "concrete", "role": "primary"}])
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_quantitative_data", lambda s: [1])
    monkeypatch.setattr(scrape_pdfs_parallel, "confidence_score", lambda *a, **k: "med")
    monkeypatch.setattr(scrape_pdfs_parallel, "normalize_event_key", lambda *a, **k: "key")
    monkeypatch.setattr(scrape_pdfs_parallel, "ConfidenceInput", lambda **kwargs: kwargs)
    monkeypatch.setattr(scrape_pdfs_parallel, "link_event_tag", lambda *a, **k: None)
    monkeypatch.setattr(scrape_pdfs_parallel, "link_event_entity", lambda *a, **k: None)
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_measurement", lambda *a, **k: None)

    pdf_one = tmp_path / "copy-one.pdf"
    pdf_two = tmp_path / "copy-two.pdf"
    pdf_one.write_bytes(b"%PDF-1.4\n%EOF one")
    pdf_two.write_bytes(b"%PDF-1.4\n%EOF two with different bytes")
    db_path = tmp_path / "db.sqlite"
    db_path.touch()

    scrape_pdfs_parallel.process_single_pdf((str(pdf_one), "domain", str(db_path)))
    scrape_pdfs_parallel.process_single_pdf((str(pdf_two), "domain", str(db_path)))

    assert upsert_source.call_count == 2
    first_source_id = upsert_source.call_args_list[0][0][1]
    second_source_id = upsert_source.call_args_list[1][0][1]
    assert first_source_id == second_source_id == "10.1234/example"


def test_process_single_pdf_skips_low_confidence(monkeypatch, tmp_path):
    monkeypatch.setattr(scrape_pdfs_parallel, "chunk_sentences", lambda text: ["Concrete wall assembly failed under load."])
    monkeypatch.setattr(scrape_pdfs_parallel, "_has_signal", lambda s: True)
    dummy_pdf = DummyPDF([DummyPage("test text")])
    monkeypatch.setattr(scrape_pdfs_parallel, "pdfplumber", types.SimpleNamespace(open=lambda *a, **k: dummy_pdf))
    monkeypatch.setattr(scrape_pdfs_parallel, "_connect", lambda db: sqlite3.connect(db))
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_metadata", lambda *a, **k: {})
    monkeypatch.setattr(scrape_pdfs_parallel, "upsert_source", lambda *a, **k: "sid")
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_document", lambda *a, **k: "did")
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_chunk", lambda *a, **k: "cid")
    insert_event = MagicMock(return_value="eid")
    monkeypatch.setattr(scrape_pdfs_parallel, "insert_event", insert_event)
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_method_tags", lambda s: [])
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_failure_reason", lambda s: "")
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_decision", lambda s: ("", None))
    monkeypatch.setattr(scrape_pdfs_parallel, "detect_outcome", lambda s: "")
    monkeypatch.setattr(scrape_pdfs_parallel, "guess_stage", lambda s: "")
    monkeypatch.setattr(scrape_pdfs_parallel, "classify_event_type", lambda *a, **k: "type")
    monkeypatch.setattr(scrape_pdfs_parallel, "evidence_strength", lambda s: "weak")
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_entities", lambda s, d: [{"entity_type": "t", "entity_name": "n"}])
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_quantitative_data", lambda s: [])
    monkeypatch.setattr(scrape_pdfs_parallel, "confidence_score", lambda *a, **k: "low")
    monkeypatch.setattr(scrape_pdfs_parallel, "normalize_event_key", lambda *a, **k: "key")
    monkeypatch.setattr(scrape_pdfs_parallel, "ConfidenceInput", lambda **kwargs: kwargs)

    pdf_path = tmp_path / "f.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%EOF")
    db_path = tmp_path / "db.sqlite"
    db_path.touch()
    result = scrape_pdfs_parallel.process_single_pdf((str(pdf_path), "domain", str(db_path)))

    assert result[2] is True
    assert result[1] == 0
    insert_event.assert_not_called()


def test_main_rejects_entity_name_domain(monkeypatch):
    monkeypatch.setattr(scrape_pdfs_parallel.sys, "argv", ["prog", "--domain", "peptide"])
    with pytest.raises(SystemExit):
        scrape_pdfs_parallel.main()


def test_main_triangulates_construction_cache_before_processing(monkeypatch, tmp_path):
    input_dir = tmp_path / "cache" / "rss"
    input_dir.mkdir(parents=True)
    keep_pdf = input_dir / "keep.pdf"
    skip_pdf = input_dir / "skip.pdf"
    keep_pdf.write_bytes(b"%PDF-1.4 keep")
    skip_pdf.write_bytes(b"%PDF-1.4 skip")

    output_db = tmp_path / "db.sqlite"
    captured_jobs = []

    triage_map = {
        keep_pdf: TriagedSource(
            file_path=str(keep_pdf),
            title="Keep paper",
            detected_domain="construction_science",
            keep_skip_review="review",
            confidence="med",
            construction_signals="wall",
            contamination_signals="",
            reason="construction-oriented",
        ),
        skip_pdf: TriagedSource(
            file_path=str(skip_pdf),
            title="Skip paper",
            detected_domain="biomedical",
            keep_skip_review="skip",
            confidence="high",
            construction_signals="",
            contamination_signals="stem cell",
            reason="biomedical contamination",
        ),
    }

    monkeypatch.setattr(scrape_pdfs_parallel, "scan_pdf", lambda pdf_path, first_pages=4, max_chars=3000: triage_map[pdf_path])

    def fake_process_single_pdf(job):
        captured_jobs.append(job)
        return (Path(job[0]).name, 0, True, "")

    class _FakePool:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def imap_unordered(self, func, jobs):
            return [func(job) for job in jobs]

    monkeypatch.setattr(scrape_pdfs_parallel, "process_single_pdf", fake_process_single_pdf)
    monkeypatch.setattr(scrape_pdfs_parallel, "Pool", _FakePool)
    monkeypatch.setattr(scrape_pdfs_parallel, "tqdm", lambda iterable, **kwargs: iterable)
    monkeypatch.setattr(scrape_pdfs_parallel.sys, "argv", [
        "prog",
        "--domain",
        "construction_science",
        "--input-dir",
        str(input_dir),
        "--output-db",
        str(output_db),
        "--workers",
        "1",
    ])

    scrape_pdfs_parallel.main()

    assert captured_jobs == [(str(keep_pdf), "construction_science", str(output_db))]
