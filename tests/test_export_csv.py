import tempfile
from pathlib import Path
from utils import export_csv
from unittest.mock import MagicMock

def test_export_candidates_domain_aware_smoke(monkeypatch):
    # Patch DB_PATH to a temp file and patch sqlite3.connect to avoid real DB
    monkeypatch.setattr(export_csv, "DB_PATH", Path(tempfile.gettempdir()) / "fake.sqlite")
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_con.__enter__.return_value = mock_con
    mock_con.__exit__.return_value = None
    mock_con.cursor.return_value = mock_cursor
    mock_cursor.execute.return_value = mock_cursor  # Real sqlite3 returns cursor from execute
    mock_cursor.fetchone.return_value = (0,)
    mock_cursor.fetchall.return_value = []
    monkeypatch.setattr(export_csv.sqlite3, "connect", lambda *a, **k: mock_con)
    # Should not raise
    export_csv.export_candidates_domain_aware(domain_id="test_domain")
    # Assert connect was called
    assert mock_con.cursor.called
    assert mock_cursor.execute.called
