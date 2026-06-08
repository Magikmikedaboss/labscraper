

import gc
import pytest
import sqlite3
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from pdfplumber.utils.exceptions import PdfminerException
from utils.source_triage import TriagedSource

from utils.run_engine import main
from utils.db_init import init_db_schema

def test_main_function_falsy_domain_uses_default():
    # NOTE: This test intentionally omits an explicit init_db_schema() call.
    # main() internally calls _init_db_schema_if_needed(), which initializes the schema for non-canonical/test DBs.
    # This ensures the test exercises main()'s fallback DB initialization logic as intended.
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        output_db = Path(temp_dir) / "test_output.sqlite"

        # Create a mock PDF file
        test_pdf = input_dir / "test.pdf"
        test_pdf.write_bytes(b"Mock PDF content")

        # Should handle falsy domain gracefully (uses default/fallback)
        with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
             patch('utils.run_engine.extract_metadata') as mock_metadata, \
             patch('utils.run_engine.chunk_sentences') as mock_sentences:

            mock_pdf = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test content"
            mock_pdf.pages = [mock_page]
            mock_pdf.metadata = {}
            mock_pdf_open.return_value.__enter__.return_value = mock_pdf
            mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
            mock_sentences.return_value = ['Test sentence.']

            main(
                domain='',  # Falsy domain triggers fallback
                input_dir=str(input_dir),
                db_path=str(output_db)
            )

        assert output_db.exists()

        # Ensure all connections are closed and garbage collected (Windows fix)
        gc.collect()

def test_main_function_database_creation():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        output_db = Path(temp_dir) / "test_output.sqlite"
        init_db_schema(str(output_db))

        test_pdf = input_dir / "test.pdf"
        test_pdf.write_bytes(b"Mock PDF content")

        with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
             patch('utils.run_engine.extract_metadata') as mock_metadata, \
             patch('utils.run_engine.chunk_sentences') as mock_sentences:

            mock_pdf = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test content"
            mock_pdf.pages = [mock_page]
            mock_pdf.metadata = {}
            mock_pdf_open.return_value.__enter__.return_value = mock_pdf
            mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
            mock_sentences.return_value = ['Test sentence.']

            main(
                domain='methods_tooling',
                input_dir=str(input_dir),
                db_path=str(output_db)
            )

        assert output_db.exists()

        conn = sqlite3.connect(str(output_db))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert 'sources' in tables
        assert 'documents' in tables
        assert 'research_events' in tables
        assert 'entities' in tables
        assert 'event_entities' in tables
        assert 'quantitative_measurements' in tables
        assert 'entity_relationships' in tables
        conn.close()
        gc.collect()

@pytest.mark.skipif(sys.platform == "win32", reason="Windows file locking issue with SQLite")
def test_main_function_error_handling():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        output_db = Path(temp_dir) / "test_output.sqlite"
        test_pdf = input_dir / "test.pdf"
        test_pdf.write_bytes(b"Mock PDF content")

        # Ensure the DB/schema exists before main is called
        init_db_schema(str(output_db))
        with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open:
            mock_pdf_open.side_effect = Exception("Processing error")
            with pytest.raises(Exception, match="Processing error"):
                main(
                    domain='methods_tooling',
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
        gc.collect()
        assert output_db.exists()

def test_main_function_multiple_pdfs():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        output_db = Path(temp_dir) / "test_output.sqlite"
        init_db_schema(str(output_db))

        for i in range(2):
            test_pdf = input_dir / f"test_{i}.pdf"
            test_pdf.write_bytes(f"Mock PDF content {i}".encode("utf-8"))


        with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
             patch('utils.run_engine.extract_metadata') as mock_metadata, \
             patch('utils.run_engine.chunk_sentences') as mock_sentences:

            mock_pdf = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test content"
            mock_pdf.pages = [mock_page]
            mock_pdf.metadata = {}
            mock_pdf_open.return_value.__enter__.return_value = mock_pdf
            mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
            mock_sentences.return_value = ['Test sentence.']

            main(
                domain='methods_tooling',
                input_dir=str(input_dir),
                db_path=str(output_db)
            )

        assert mock_pdf_open.call_count == 2
        gc.collect()
        assert output_db.exists()

def test_main_function_domain_specific_processing():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()
        test_pdf = input_dir / "test.pdf"
        test_pdf.write_bytes(b"Mock PDF content")
        domains = ['methods_tooling', 'drug_discovery', 'construction_science']
        for domain in domains:
            output_db = Path(temp_dir) / f"test_output_{domain}.sqlite"
            init_db_schema(str(output_db))
            with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
                 patch('utils.run_engine.extract_metadata') as mock_metadata, \
                 patch('utils.run_engine.chunk_sentences') as mock_sentences:

                mock_pdf = Mock()
                mock_page = Mock()
                mock_page.extract_text.return_value = "Test content"
                mock_pdf.pages = [mock_page]
                mock_pdf.metadata = {}
                mock_pdf_open.return_value.__enter__.return_value = mock_pdf
                mock_metadata.return_value = {'title': 'Test', 'authors': 'Test Author', 'year': 2023}
                mock_sentences.return_value = ['Test sentence.']

                main(
                    domain=domain,
                    input_dir=str(input_dir),
                    db_path=str(output_db)
                )
            gc.collect()
            assert output_db.exists()


def test_main_triangulates_construction_cache_before_processing(tmp_path, monkeypatch):
    input_dir = tmp_path / "cache" / "rss"
    input_dir.mkdir(parents=True)
    keep_pdf = input_dir / "keep.pdf"
    skip_pdf = input_dir / "skip.pdf"
    keep_pdf.write_bytes(b"%PDF-1.4 keep")
    skip_pdf.write_bytes(b"%PDF-1.4 skip")

    output_db = tmp_path / "test_output.sqlite"
    init_db_schema(str(output_db))

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

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = "Test content"
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    monkeypatch.setattr("utils.run_engine.scan_pdf", lambda pdf_path, first_pages=4, max_chars=3000: triage_map[pdf_path])

    with patch('utils.run_engine.pdfplumber.open') as mock_pdf_open, \
         patch('utils.run_engine.extract_metadata', return_value={'title': 'Test', 'authors': 'Test Author', 'year': 2023}), \
         patch('utils.run_engine.chunk_sentences', return_value=['Test sentence.']):
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        main(domain='construction_science', input_dir=str(input_dir), db_path=str(output_db))

    assert mock_pdf_open.call_count == 1


def test_main_raises_when_pdf_fails(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    output_db = tmp_path / "test_output.sqlite"
    init_db_schema(str(output_db))

    bad_pdf = input_dir / "bad.pdf"
    good_pdf = input_dir / "good.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4 bad")
    good_pdf.write_bytes(b"%PDF-1.4 good")

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = "Test content"
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    class _PdfCtx:
        def __init__(self, pdf_obj):
            self._pdf = pdf_obj

        def __enter__(self):
            return self._pdf

        def __exit__(self, exc_type, exc, tb):
            return False

    def open_side_effect(path):
        if str(path).endswith("bad.pdf"):
            raise Exception("Simulated per-file failure")
        return _PdfCtx(mock_pdf)

    with patch("utils.run_engine.pdfplumber.open", side_effect=open_side_effect) as mock_pdf_open, \
         patch("utils.run_engine.extract_metadata", return_value={"title": "T", "authors": "A", "year": 2023}), \
         patch("utils.run_engine.chunk_sentences", return_value=["Test sentence."]):
        with pytest.raises(Exception, match="Simulated per-file failure"):
            main(domain="methods_tooling", input_dir=str(input_dir), db_path=str(output_db))

    assert mock_pdf_open.call_count == 1
    assert output_db.exists()


def test_main_exits_1_when_all_pdfs_fail(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    output_db = tmp_path / "test_output.sqlite"
    init_db_schema(str(output_db))

    (input_dir / "a.pdf").write_bytes(b"%PDF-1.4 a")
    (input_dir / "b.pdf").write_bytes(b"%PDF-1.4 b")

    with patch("utils.run_engine.pdfplumber.open", side_effect=Exception("Processing error")):
        with pytest.raises(Exception, match="Processing error"):
            main(domain="methods_tooling", input_dir=str(input_dir), db_path=str(output_db))


def test_main_skips_pdfminer_exception_and_exits_1_when_all_pdfs_fail(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    output_db = tmp_path / "test_output.sqlite"
    init_db_schema(str(output_db))

    (input_dir / "bad.pdf").write_bytes(b"%PDF-1.4 bad")

    with patch("utils.run_engine.pdfplumber.open", side_effect=PdfminerException("No /Root object! - Is this really a PDF?")):
        with pytest.raises(SystemExit, match=r"1"):
            main(domain="methods_tooling", input_dir=str(input_dir), db_path=str(output_db))


def test_main_invalid_domain_exits_with_error(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    output_db = tmp_path / "test_output.sqlite"
    init_db_schema(str(output_db))

    pdf_path = input_dir / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 content")

    with pytest.raises(SystemExit, match=r"Unknown domain 'not_a_real_domain'"):
        main(domain="not_a_real_domain", input_dir=str(input_dir), db_path=str(output_db))


def test_main_duplicate_pdf_content_uses_same_source_id(tmp_path):
    input_dir = tmp_path / "input_pdfs"
    input_dir.mkdir()
    output_db = tmp_path / "test_output.sqlite"
    init_db_schema(str(output_db))

    duplicate_bytes = b"%PDF-1.4 same-content"
    (input_dir / "first.pdf").write_bytes(duplicate_bytes)
    (input_dir / "second.pdf").write_bytes(duplicate_bytes)

    mock_pdf = Mock()
    mock_page = Mock()
    mock_page.extract_text.return_value = ""
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {}

    with patch("utils.run_engine.pdfplumber.open") as mock_pdf_open, \
         patch("utils.run_engine.extract_metadata", return_value={"title": "T", "authors": "A", "year": 2023}), \
         patch("utils.run_engine.chunk_sentences", return_value=[]):
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        main(domain="methods_tooling", input_dir=str(input_dir), db_path=str(output_db))

    with sqlite3.connect(str(output_db)) as con:
        sources_count = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        documents_count = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # Same content hash should dedupe both source and document rows.
    assert sources_count == 1
    assert documents_count == 1
