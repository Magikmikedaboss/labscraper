import sqlite3
from utils import scrape_pdfs_parallel
import types
from unittest.mock import MagicMock

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
    monkeypatch.setattr(scrape_pdfs_parallel, "chunk_sentences", lambda text: ["This is a test sentence."])
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
    monkeypatch.setattr(scrape_pdfs_parallel, "extract_entities", lambda s, d: [{"entity_type": "t", "entity_name": "n", "role": "primary"}])
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
