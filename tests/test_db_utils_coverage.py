from utils.db_utils import connect_db, get_tables, get_table_stats

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

# TODO: Add more tests for the following functions to improve coverage:
#   - show_recent_events
#   - show_top_sources
#   - show_pdf_cache
#   - insert_document, insert_chunk, insert_event, link_event_entity, link_event_tag, insert_measurement, upsert_entity
#   - Any other insert/upsert/link utility functions in utils.db_utils
# This ensures coverage for all major DB utility operations and reporting helpers.
