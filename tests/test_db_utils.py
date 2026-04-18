import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

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

    def test_connect_db_valid_path(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            assert isinstance(conn, sqlite3.Connection)
            conn.close()
        finally:
            os.unlink(db_path)

    def test_connect_db_nonexistent_path(self):
        with pytest.raises(FileNotFoundError):
            connect_db("nonexistent_database.sqlite")


# ---------------------------------------------------------
# TABLE TESTS
# ---------------------------------------------------------
class TestGetTables:

    def test_empty_database(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            tables = get_tables(conn)
            assert tables == []
            conn.close()
        finally:
            os.unlink(db_path)

    def test_with_tables(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            conn.execute("CREATE TABLE test1 (id INTEGER)")
            conn.execute("CREATE TABLE test2 (name TEXT)")
            conn.commit()

            tables = get_tables(conn)
            assert "test1" in tables
            assert "test2" in tables

            conn.close()
        finally:
            os.unlink(db_path)


# ---------------------------------------------------------
# TABLE STATS
# ---------------------------------------------------------
class TestGetTableStats:

    def test_valid_table(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'a')")
            conn.execute("INSERT INTO test VALUES (2, 'b')")
            conn.commit()

            stats = get_table_stats(conn, "test")

            assert stats["count"] == 2
            assert "id" in stats["columns"]
            assert "name" in stats["columns"]

            conn.close()
        finally:
            os.unlink(db_path)

    def test_nonexistent_table(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.commit()

            with pytest.raises(ValueError):
                get_table_stats(conn, "fake_table")

            conn.close()
        finally:
            os.unlink(db_path)


# ---------------------------------------------------------
# INSPECT DB
# ---------------------------------------------------------
class TestInspectDatabase:

    def test_runs_without_crash(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            conn.close()

            inspect_database(db_path, detailed=False)

        finally:
            os.unlink(db_path)


# ---------------------------------------------------------
# DISPLAY FUNCTIONS
# ---------------------------------------------------------
class TestDisplayFunctions:

    def test_recent_events(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            apply_schema(conn)
            show_recent_events(conn)
            conn.close()
        finally:
            os.unlink(db_path)

    def test_top_sources(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            apply_schema(conn)
            show_top_sources(conn)
            conn.close()
        finally:
            os.unlink(db_path)


# ---------------------------------------------------------
# DISTRIBUTIONS
# ---------------------------------------------------------
class TestDistributions:

    def test_event_type_distribution(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            apply_schema(conn)
            get_event_type_distribution(conn)
            conn.close()
        finally:
            os.unlink(db_path)

    def test_domain_distribution(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = connect_db(db_path)
            apply_schema(conn)
            get_domain_distribution(conn)
            conn.close()
        finally:
            os.unlink(db_path)