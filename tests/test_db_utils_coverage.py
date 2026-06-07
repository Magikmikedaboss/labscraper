import logging
import pytest

from utils import db_utils
from utils.db_utils import connect_db, get_table_stats, get_tables

def test_connect_db_and_get_tables(init_test_schema):
    db_path = init_test_schema
    conn = connect_db(str(db_path))
    try:
        tables = get_tables(conn)
        assert "sources" in tables
        stats = get_table_stats(conn, "sources")
        assert "source_id" in stats["columns"]
    finally:
        conn.close()

def test_show_recent_events_and_top_sources(init_test_schema, caplog):
    db_path = init_test_schema
    conn = db_utils.connect_db(str(db_path))
    try:
        # Insert minimal required data
        conn.execute("INSERT INTO sources (source_id, title) VALUES (?, ?)", ("SRC1", "Test Source"))
        conn.execute("""
            INSERT INTO research_events (
                event_id, research_domain, event_type, stage, system_context, application_context,
                outcome, failure_reason, decision_taken, decision_driver,
                evidence_snippet, evidence_strength, confidence,
                source_id, doc_id, chunk_id, page_number, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "EVT1", "domain", "etype", "stage", "system", "area",
            "outcome", "fail", "decision", "driver",
            "evidence", "strong", "high",
            "SRC1", None, None, 1, "2024-01-01T00:00:00"
        ))
        conn.commit()
        with caplog.at_level(logging.INFO):
            db_utils.show_recent_events(conn)
            db_utils.show_top_sources(conn)
        output = " ".join([r.getMessage() for r in caplog.records])
        assert "RECENT EVENTS" in output
        assert "TOP SOURCES" in output
        assert "Test Source" in output
    finally:
        conn.close()

def test_show_pdf_cache(tmp_path, caplog, init_test_schema):
    cache_dir = tmp_path / "rss_cache"
    cache_dir.mkdir()
    # Create a fake PDF file
    pdf_file = cache_dir / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")
    # Setup DB connection and insert required source/document
    db_path = init_test_schema
    conn = db_utils.connect_db(str(db_path))
    try:
        db_utils.upsert_source(conn, "SRC2", "file.pdf", {"title": "T", "authors": "A", "year": 2020, "doi": "D"})
        doc_id = db_utils.insert_document(conn, "SRC2", "file.pdf", "sha256abc")
        with caplog.at_level(logging.INFO):
            db_utils.show_pdf_cache(str(cache_dir))
        output = " ".join([r.getMessage() for r in caplog.records])
        assert "PDF CACHE" in output
        # Insert chunk
        chunk_id = db_utils.insert_chunk(conn, "SRC2", doc_id, 1, "Methods", "Some chunk text.")
        assert isinstance(chunk_id, str)
        # Upsert entity
        entity_id = db_utils.upsert_entity(conn, "compound", "aspirin", None, None)
        assert isinstance(entity_id, str)
        # Insert event
        event_id = db_utils.insert_event(
            con=conn,
            source_id="SRC2",
            doc_id=doc_id,
            chunk_id=chunk_id,
            page_number=1,
            domain="domain",
            event_type="type",
            stage="stage",
            system_context=None,
            application_context=None,
            outcome="ok",
            failure_reason="none",
            decision_taken="yes",
            decision_driver=None,
            evidence_snippet="evidence",
            evidence_strength_v="strong",
            confidence_v="high",
        )
        assert isinstance(event_id, str)
        # Link event to entity
        db_utils.link_event_entity(conn, event_id, entity_id, "primary")
        # Link event tag
        db_utils.link_event_tag(conn, event_id, "tag1")
        # Insert measurement (valid)
        db_utils.insert_measurement(conn, event_id, {"measurement_type": "IC50", "value": "5.0", "unit": "uM", "context": "IC50 = 5.0 uM"})
        # Insert measurement (missing required fields)
        with pytest.raises(ValueError) as excinfo:
            db_utils.insert_measurement(conn, event_id, {"measurement_type": None, "value": None, "unit": None})
        assert "Missing required measurement fields" in str(excinfo.value)
    finally:
        conn.close()


def test_upsert_source_finds_fuzzy_match_beyond_first_thousand_rows(init_test_schema):
    conn = db_utils.connect_db(str(init_test_schema))
    try:
        target_title = "x" * 100 + "a"
        fuzzy_title = "x" * 100 + "b"

        rows = [(f"SRC{i}", f"unrelated title {i}") for i in range(1000)]
        rows.append(("SRC_MATCH", fuzzy_title))
        conn.executemany("INSERT INTO sources (source_id, title) VALUES (?, ?)", rows)
        conn.commit()

        resolved = db_utils.upsert_source(
            conn,
            "NEW_SOURCE",
            "paper.pdf",
            {"title": target_title},
        )

        assert resolved == "SRC_MATCH"
    finally:
        conn.close()


def test_upsert_source_creates_normalized_title_index(init_test_schema):
    conn = db_utils.connect_db(str(init_test_schema))
    try:
        db_utils.upsert_source(conn, "SRC_IDX", "paper.pdf", {"title": "Index Title"})
        index_names = {
            row[1]
            for row in conn.execute("PRAGMA index_list('sources')").fetchall()
        }

        assert "idx_sources_title_norm" in index_names
    finally:
        conn.close()
