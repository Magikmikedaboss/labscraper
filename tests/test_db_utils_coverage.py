
from utils.db_utils import connect_db, get_tables, get_table_stats

def test_connect_db_and_get_tables(init_test_schema):
    db_path = init_test_schema
    conn = connect_db(str(db_path))
    tables = get_tables(conn)
    assert "sources" in tables
    stats = get_table_stats(conn, "sources")
    assert "source_id" in stats["columns"]
    conn.close()

# Add more tests for show_recent_events, show_top_sources, show_pdf_cache, and all insert/upsert/link functions
# to cover lines 34, 72–74, 78–81, 97–101, 121–124, 130–148, 164–165, 183–184, 202–203, 209, 217–223, 226–232, 235, 238–245, 251–267, 270, 277–278, 286–287, 298–299
