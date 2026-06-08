from utils.db_utils import inspect_database
import utils.db_utils as db_utils
import sqlite3
import re
import pytest

# Test for inspect_database function in utils/db_utils.py
def test_inspect_database_basic(init_test_schema, caplog):
    # Use the shared schema fixture to create a DB
    db_path = init_test_schema
    # Should log table info
    with caplog.at_level("INFO"):
        inspect_database(str(db_path), detailed=True)
    log_output = "\n".join(caplog.messages)
    assert "DATABASE INSPECTION" in log_output
    assert "Tables found" in log_output
    assert "sources" in log_output


def test_inspect_database_missing_db_returns_empty_result(tmp_path, caplog):
    missing_db = tmp_path / "missing.sqlite"
    with caplog.at_level("ERROR"):
        result = inspect_database(str(missing_db), detailed=False)

    assert result["db_path"] == str(missing_db)
    assert result["tables"] == []
    assert any("Database not found" in msg for msg in caplog.messages)


def test_inspect_database_empty_db_logs_zero_tables(tmp_path, caplog):
    db_path = tmp_path / "empty.sqlite"
    with sqlite3.connect(db_path):
        pass

    with caplog.at_level("INFO"):
        result = inspect_database(str(db_path), detailed=False)

    assert result["db_path"] == str(db_path)
    assert result["tables"] == []
    assert any("Tables found: 0" in msg for msg in caplog.messages)


def test_inspect_database_corrupt_db_returns_empty_result(tmp_path, caplog):
    db_path = tmp_path / "corrupt.sqlite"
    db_path.write_bytes(b"not a sqlite database")

    with caplog.at_level("ERROR"):
        result = inspect_database(str(db_path), detailed=False)

    assert result["db_path"] == str(db_path)
    assert result["tables"] == []
    assert any("Database error" in msg for msg in caplog.messages)


def test_inspect_database_invalid_db_path_type_raises_type_error():
    with pytest.raises(TypeError):
        inspect_database(None)


def test_inspect_database_handles_many_tables(tmp_path, caplog):
    db_path = tmp_path / "many_tables.sqlite"
    with sqlite3.connect(db_path) as con:
        table_names = [f"t_{idx}" for idx in range(60)]
        for table_name in table_names:
            # Safe because table_name is validated with re.fullmatch(r"t_\d+", table_name) before use.
            # Do not remove or bypass that regex check if this f-string pattern is reused elsewhere.
            assert re.fullmatch(r"t_\d+", table_name)
            con.execute(f"CREATE TABLE {table_name} (id INTEGER)")

    with caplog.at_level("INFO"):
        result = inspect_database(str(db_path), detailed=False)

    assert len(result["tables"]) == 60
    assert any("Tables found: 60" in msg for msg in caplog.messages)


def test_inspect_database_permission_error_returns_empty_result(monkeypatch, caplog):
    def _raise_permission_error(_db_path):
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(db_utils, "connect_db", _raise_permission_error)

    with caplog.at_level("ERROR"):
        result = inspect_database("db/protected.sqlite", detailed=False)

    assert result["db_path"] == "db/protected.sqlite"
    assert result["tables"] == []
    assert any("Database error" in msg for msg in caplog.messages)


def test_inspect_database_handles_large_result_set(tmp_path, caplog):
    db_path = tmp_path / "large_rows.sqlite"
    with sqlite3.connect(db_path) as con:
        con.execute("CREATE TABLE big_rows (id INTEGER)")
        con.executemany("INSERT INTO big_rows (id) VALUES (?)", [(i,) for i in range(12345)])

    with caplog.at_level("INFO"):
        result = inspect_database(str(db_path), detailed=False)

    assert "big_rows" in result["tables"]
    assert any("Rows: 12,345" in msg for msg in caplog.messages)


def test_inspect_database_detailed_logs_columns(tmp_path, caplog):
    db_path = tmp_path / "detailed.sqlite"
    with sqlite3.connect(db_path) as con:
        con.execute("CREATE TABLE details_table (id INTEGER, label TEXT)")

    with caplog.at_level("INFO"):
        result = inspect_database(str(db_path), detailed=True)

    assert "details_table" in result["tables"]
    assert any("Columns: id, label" in msg for msg in caplog.messages)
