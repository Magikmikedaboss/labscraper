
from utils.db_utils import (
    connect_db,
    get_tables,
    get_table_stats,
    inspect_database,
    show_recent_events,
    show_top_sources,
    get_event_type_distribution,
    get_domain_distribution,
)

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
# ---------------------------------------------------------
# TEST DB FIXTURE
# ---------------------------------------------------------
@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        db_path = tmp.name
    try:
        conn = connect_db(db_path)
        yield conn
        conn.close()
    finally:
        os.unlink(db_path)


# ---------------------------------------------------------
# SCHEMA HELPER
# ---------------------------------------------------------
def apply_schema(conn):
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema.sql at {schema_path}")

    conn.executescript(schema_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------
# CONNECT DB TESTS
# ---------------------------------------------------------
class TestConnectDB:


    def test_connect_db_valid_path(self, temp_db):
        assert isinstance(temp_db, sqlite3.Connection)

    def test_connect_db_nonexistent_path(self):
        with pytest.raises(FileNotFoundError):
            connect_db("nonexistent_database.sqlite")


# ---------------------------------------------------------
# TABLE TESTS
# ---------------------------------------------------------
class TestGetTables:


    def test_empty_database(self, temp_db):
        tables = get_tables(temp_db)
        assert tables == []


    def test_with_tables(self, temp_db):
        temp_db.execute("CREATE TABLE test1 (id INTEGER)")
        temp_db.execute("CREATE TABLE test2 (name TEXT)")
        temp_db.commit()
        tables = get_tables(temp_db)
        assert "test1" in tables
        assert "test2" in tables


# ---------------------------------------------------------
# TABLE STATS
# ---------------------------------------------------------
class TestGetTableStats:


    def test_valid_table(self, temp_db):
        temp_db.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        temp_db.execute("INSERT INTO test VALUES (1, 'a')")
        temp_db.execute("INSERT INTO test VALUES (2, 'b')")
        temp_db.commit()
        stats = get_table_stats(temp_db, "test")
        assert stats["count"] == 2
        assert "id" in stats["columns"]
        assert "name" in stats["columns"]


    def test_nonexistent_table(self, temp_db):
        temp_db.execute("CREATE TABLE test (id INTEGER)")
        temp_db.commit()
        with pytest.raises(ValueError):
            get_table_stats(temp_db, "fake_table")


# ---------------------------------------------------------
# INSPECT DB
# ---------------------------------------------------------
class TestInspectDatabase:


    def test_runs_without_crash(self, temp_db):
        db_path = temp_db.execute('PRAGMA database_list').fetchone()[2]
        # Do not close temp_db here; open a new connection for inspect_database if needed
        result = inspect_database(db_path, detailed=False)
        assert isinstance(result, (dict, list, type(None)))


# ---------------------------------------------------------
# DISPLAY FUNCTIONS
# ---------------------------------------------------------
class TestDisplayFunctions:


    def test_recent_events(self, temp_db):
        apply_schema(temp_db)
        show_recent_events(temp_db)


    def test_top_sources(self, temp_db):
        apply_schema(temp_db)
        show_top_sources(temp_db)


# ---------------------------------------------------------
# DISTRIBUTIONS
# ---------------------------------------------------------
class TestDistributions:



    def test_event_type_distribution(self, temp_db):
        apply_schema(temp_db)
        result = get_event_type_distribution(temp_db)
        assert result is None



    def test_domain_distribution(self, temp_db):
        apply_schema(temp_db)
        result = get_domain_distribution(temp_db)
        assert result is None