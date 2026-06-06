import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, Mock
import gc

from utils.run_engine import main


def test_main_function_database_creation():
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = Path(temp_dir) / "input_pdfs"
        input_dir.mkdir()

        output_db = Path(temp_dir) / "test_output.sqlite"

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
            mock_pdf_open.return_value.__exit__.return_value = False
            mock_metadata.return_value = {
                'title': 'Test',
                'authors': 'Test Author',
                'year': 2023
            }
            mock_sentences.return_value = ['Test sentence.']

            main(
                domain='methods_tooling',
                input_dir=str(input_dir),
                db_path=str(output_db)
            )

        assert output_db.exists()

        conn = sqlite3.connect(str(output_db))
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert 'sources' in tables
            assert 'documents' in tables
        finally:
            conn.close()

        # Run garbage collection after all context managers and connection cleanup
        gc.collect()


