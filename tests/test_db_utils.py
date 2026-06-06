
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
        conn = sqlite3.connect(db_path)
        yield conn, db_path
        conn.close()
    finally:
        os.unlink(db_path)


# ---------------------------------------------------------
# SCHEMA HELPER
# ---------------------------------------------------------
def apply_schema(conn):
    current = Path(__file__).resolve().parent
    while True:
        schema_path = current / "schema.sql"
        if schema_path.exists():
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            return
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError(f"Could not find schema.sql searching upward from {Path(__file__).resolve().parent}")


# ---------------------------------------------------------
# CONNECT DB TESTS
# ---------------------------------------------------------
class TestConnectDB:


    def test_connect_db_valid_path(self, temp_db):
        conn, db_path = temp_db
        conn.close()
        opened = connect_db(db_path)
        try:
            assert isinstance(opened, sqlite3.Connection)
        finally:
            opened.close()

    def test_connect_db_nonexistent_path(self):
        with pytest.raises(FileNotFoundError):
            connect_db("nonexistent_database.sqlite")


# ---------------------------------------------------------
# TABLE TESTS
# ---------------------------------------------------------
class TestGetTables:


    def test_empty_database(self, temp_db):
        conn, db_path = temp_db
        tables = get_tables(conn)
        assert tables == []


    def test_with_tables(self, temp_db):
        conn, db_path = temp_db
        conn.execute("CREATE TABLE test1 (id INTEGER)")
        conn.execute("CREATE TABLE test2 (name TEXT)")
        conn.commit()
        tables = get_tables(conn)
        assert "test1" in tables
        assert "test2" in tables


# ---------------------------------------------------------
# TABLE STATS
# ---------------------------------------------------------
class TestGetTableStats:


    def test_valid_table(self, temp_db):
        conn, db_path = temp_db
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'a')")
        conn.execute("INSERT INTO test VALUES (2, 'b')")
        conn.commit()
        stats = get_table_stats(conn, "test")
        assert stats["count"] == 2
        assert "id" in stats["columns"]
        assert "name" in stats["columns"]


    def test_nonexistent_table(self, temp_db):
        conn, db_path = temp_db
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        with pytest.raises(ValueError):
            get_table_stats(conn, "fake_table")


# ---------------------------------------------------------
# INSPECT DB
# ---------------------------------------------------------
class TestInspectDatabase:


    def test_runs_without_crash(self, temp_db):
        conn, db_path = temp_db
        # Do not close conn here; open a new connection for inspect_database if needed
        result = inspect_database(db_path, detailed=False)
        assert isinstance(result, (dict, list, type(None)))


# ---------------------------------------------------------
# DISPLAY FUNCTIONS
# ---------------------------------------------------------
class TestDisplayFunctions:


    def test_recent_events(self, temp_db, caplog):
        conn, db_path = temp_db
        apply_schema(conn)
        # Insert a test event and required source
        conn.execute("INSERT INTO sources (source_id, title) VALUES (?, ?)", ("SRC1", "Test Source"))
        conn.execute("""
            INSERT INTO research_events (
                event_id, research_domain, event_type, stage, system_context, application_context,
                outcome, failure_reason, decision_taken, decision_driver,
                evidence_snippet, evidence_strength, confidence,
                source_id, doc_id, chunk_id, page_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "EVT1", "test_domain", "test_type", "stage1", "system1", "area1",
            "outcome1", "fail1", "decision1", "driver1",
            "evidence1", "strong", "high",
            "SRC1", None, None, 1, "2024-01-01T00:00:00"
        ))
        conn.commit()
        with caplog.at_level("INFO"):
            show_recent_events(conn)
        # Assert output contains expected event type and domain
        output = " ".join([r.getMessage() for r in caplog.records])
        assert "RECENT EVENTS" in output
        assert "test_type" in output
        assert "test_domain" in output

    def test_top_sources(self, temp_db, caplog):
        conn, db_path = temp_db
        apply_schema(conn)
        # Insert a test source and event
        conn.execute("INSERT INTO sources (source_id, title) VALUES (?, ?)", ("SRC2", "Source Title"))
        conn.execute("""
            INSERT INTO research_events (
                event_id, research_domain, event_type, stage, system_context, application_context,
                outcome, failure_reason, decision_taken, decision_driver,
                evidence_snippet, evidence_strength, confidence,
                source_id, doc_id, chunk_id, page_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "EVT2", "domain2", "type2", "stage2", "system2", "area2",
            "outcome2", "fail2", "decision2", "driver2",
            "evidence2", "moderate", "med",
            "SRC2", None, None, 2, "2024-01-02T00:00:00"
        ))
        conn.commit()
        with caplog.at_level("INFO"):
            show_top_sources(conn)
        output = " ".join([r.getMessage() for r in caplog.records])
        assert "TOP SOURCES" in output
        assert "Source Title" in output


# ---------------------------------------------------------
# DISTRIBUTIONS
# ---------------------------------------------------------
class TestDistributions:



    def test_event_type_distribution(self, temp_db, caplog):
        conn, db_path = temp_db
        apply_schema(conn)
        # Insert a test event
        conn.execute("INSERT INTO sources (source_id, title) VALUES (?, ?)", ("SRC3", "Source3"))
        conn.execute("""
            INSERT INTO research_events (
                event_id, research_domain, event_type, stage, system_context, application_context,
                outcome, failure_reason, decision_taken, decision_driver,
                evidence_snippet, evidence_strength, confidence,
                source_id, doc_id, chunk_id, page_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "EVT3", "domain3", "etype", "stage3", "system3", "area3",
            "outcome3", "fail3", "decision3", "driver3",
            "evidence3", "weak", "low",
            "SRC3", None, None, 3, "2024-01-03T00:00:00"
        ))
        conn.commit()
        with caplog.at_level("INFO"):
            get_event_type_distribution(conn)
        output = " ".join([r.getMessage() for r in caplog.records])
        assert "EVENT TYPE DISTRIBUTION" in output
        assert "etype" in output



    def test_domain_distribution(self, temp_db, caplog):
        conn, db_path = temp_db
        apply_schema(conn)
        # Insert a test event
        conn.execute("INSERT INTO sources (source_id, title) VALUES (?, ?)", ("SRC4", "Source4"))
        conn.execute("""
            INSERT INTO research_events (
                event_id, research_domain, event_type, stage, system_context, application_context,
                outcome, failure_reason, decision_taken, decision_driver,
                evidence_snippet, evidence_strength, confidence,
                source_id, doc_id, chunk_id, page_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "EVT4", "domain4", "type4", "stage4", "system4", "area4",
            "outcome4", "fail4", "decision4", "driver4",
            "evidence4", "strong", "high",
            "SRC4", None, None, 4, "2024-01-04T00:00:00"
        ))
        conn.commit()
        with caplog.at_level("INFO"):
            get_domain_distribution(conn)
        output = " ".join([r.getMessage() for r in caplog.records])
        assert "DOMAIN DISTRIBUTION" in output
        assert "domain4" in output