import csv
import io
from pathlib import Path
from unittest.mock import MagicMock

from utils import export_csv


class _NonClosingStringIO(io.StringIO):
    def close(self):
        # Keep the buffer readable after the context manager exits.
        pass

def test_export_candidates_domain_aware_smoke(monkeypatch, tmp_path):
    output_root = tmp_path
    monkeypatch.setattr(export_csv, "DB_PATH", output_root / "fake.sqlite")
    monkeypatch.setattr(export_csv, "LATEST_DIR", output_root / "exports" / "latest")

    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_con.__enter__.return_value = mock_con
    mock_con.__exit__.return_value = None
    mock_con.cursor.return_value = mock_cursor
    mock_cursor.execute.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1,)
    mock_cursor.fetchall.return_value = [
        ("entity-1", "compound", "Aspirin", "active", 2, "src-1,src-2"),
    ]
    monkeypatch.setattr(export_csv.sqlite3, "connect", lambda *a, **k: mock_con)
    monkeypatch.setattr(export_csv, "load_normalization_map", lambda: {})
    monkeypatch.setattr(export_csv, "load_overlay_aliases", lambda _domain_id: {})
    monkeypatch.setattr(export_csv, "normalize_entity", lambda entity, _norm, _aliases: entity)
    monkeypatch.setattr(export_csv, "get_entity_role", lambda _entity, _norm: "primary")
    monkeypatch.setattr(export_csv, "is_process_word", lambda _value: False)

    writes = _NonClosingStringIO()

    def fake_open(path, mode="r", newline="", encoding=None):
        assert mode == "w"
        assert Path(path) == output_root / "exports" / "latest" / "test_domain" / "entities.csv"
        assert encoding == "utf-8"
        assert newline == ""
        writes.seek(0)
        writes.truncate(0)
        return writes

    monkeypatch.setattr("builtins.open", fake_open)

    result = export_csv.export_candidates_domain_aware(domain_id="test_domain")

    assert mock_con.cursor.called
    assert mock_cursor.execute.call_count == 2
    assert mock_cursor.fetchone.call_count == 1
    assert mock_cursor.fetchall.call_count == 1
    assert mock_cursor.execute.call_args_list[0].args[0] == "SELECT COUNT(*) FROM research_events WHERE research_domain = ?"
    assert mock_cursor.execute.call_args_list[0].args[1] == ("test_domain",)
    assert "FROM entities e" in mock_cursor.execute.call_args_list[1].args[0]
    assert mock_cursor.execute.call_args_list[1].args[1] == ("test_domain", "test_domain")

    csv_output = writes.getvalue()
    rows = list(csv.reader(io.StringIO(csv_output)))
    assert rows[0] == ["entity_name", "entity_type", "entity_variant", "event_count"]
    assert rows[1] == ["Aspirin", "compound", "active", "2"]
    assert ("compound", "Aspirin") in result
    assert result[("compound", "Aspirin")]["event_count"] == 2
