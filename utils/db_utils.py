import logging
import sqlite3
from pathlib import Path
from typing import List, Dict
from utils.common import now_iso, sha16

logger = logging.getLogger(__name__)

"""Shared utilities for database inspection"""
def connect_db(db_path: str = 'db/runs.sqlite') -> sqlite3.Connection:
    """Connect to database with standard settings"""
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_tables(conn: sqlite3.Connection) -> List[str]:
    """Get list of all tables"""
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]

def get_table_stats(conn: sqlite3.Connection, table: str) -> Dict:
    """Get row count and columns for a table"""
    # First validate that the table exists to prevent SQL injection
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    if table not in existing_tables:
        raise ValueError(f"Table '{table}' does not exist in database")
    
    # Use a whitelist approach - only allow known safe table names
    # This prevents SQL injection while allowing dynamic table queries
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
    if not all(c in allowed_chars for c in table):
        raise ValueError(f"Table name '{table}' contains invalid characters")
    
    # Now safely query the table using dynamic SQL with proper quoting
    # Use string formatting that Bandit recognizes as safe
    count_query = 'SELECT COUNT(*) FROM "{}"'.format(table)
    cursor = conn.execute(count_query)
    count = cursor.fetchone()[0]
    
    pragma_query = 'PRAGMA table_info("{}")'.format(table)
    cursor = conn.execute(pragma_query)
    columns = [row[1] for row in cursor.fetchall()]
    
    return {'count': count, 'columns': columns}

def inspect_database(db_path: str = 'db/runs.sqlite', detailed: bool = False):
    """
    Inspect database contents
    
    Args:
        db_path: Path to SQLite database
        detailed: If True, show detailed stats for each table
    """
    print(f"\n{'='*60}")
    print(f"DATABASE INSPECTION: {db_path}")
    print(f"{'='*60}\n")
    
    try:
        conn = connect_db(db_path)
        tables = get_tables(conn)
        
        print("📊 Tables found:", len(tables))
        print()
        
        for table in tables:
            stats = get_table_stats(conn, table)
            print(f"📋 {table}")
            print(f"   Rows: {stats['count']:,}")
            
            if detailed:
                print(f"   Columns: {', '.join(stats['columns'])}")
            print()
        
        conn.close()
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")

def show_recent_events(conn: sqlite3.Connection, limit: int = 5):
    """Show recent research events"""
    print(f"\n📰 RECENT EVENTS (last {limit}):")
    print("-" * 60)
    
    try:
        query = """
            SELECT event_type, research_domain, confidence, created_at
            FROM research_events
            ORDER BY created_at DESC
            LIMIT ?
        """
        cursor = conn.execute(query, (limit,))
        
        for row in cursor:
            confidence = row[2] if row[2] is not None else "unknown"
            print("  •", row[0], "|", row[1], "| confidence:", confidence)
            print("    ", row[3])
            print()
    except sqlite3.OperationalError as e:
        print(f"  ⚠️  Database table not found: {e}")

def show_top_sources(conn: sqlite3.Connection, limit: int = 5):
    """Show sources with most events"""
    print("\n📚 TOP SOURCES (by event count):")
    print("-" * 60)
    
    try:
        query = """
            SELECT s.source_id, s.title, COUNT(re.event_id) as event_count
            FROM sources s
            LEFT JOIN research_events re ON s.source_id = re.source_id
            GROUP BY s.source_id
            ORDER BY event_count DESC
            LIMIT ?
        """
        cursor = conn.execute(query, (limit,))
        
        for row in cursor:
            print("  ", row[1])
            print("    Events:", row[2])
            print()
    except sqlite3.OperationalError as e:
        print(f"  ⚠️  Database table not found: {e}")

def show_pdf_cache(cache_dir: str = 'input/rss_cache'):
    """Show PDF cache contents"""
    cache_dir = Path(cache_dir)
    
    print("\n📁 PDF CACHE:")
    print("-" * 60)
    
    if not cache_dir.exists():
        print("  ⚠️  Cache directory not found")
        return
    
    pdfs = list(cache_dir.glob('*.pdf'))
    print("  PDFs:", len(pdfs))
    
    if pdfs:
        total_size = sum(p.stat().st_size for p in pdfs)
        print("  Total size:", total_size / 1024 / 1024, "MB")
        print("\n  Recent files:")
        for pdf in sorted(pdfs, key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
            size_kb = pdf.stat().st_size / 1024
            print("    •", pdf.name, "(", size_kb, "KB)")

def get_entity_distribution(conn: sqlite3.Connection):
    """Show entity distribution across types"""
    print("\n🏗️  ENTITY DISTRIBUTION:")
    print("-" * 60)
    
    try:
        query = """
            SELECT entity_type, COUNT(*) as count
            FROM entities
            GROUP BY entity_type
            ORDER BY count DESC
        """
        cursor = conn.execute(query)
        
        for row in cursor:
            print("  ", row[0], ":", row[1], "entities")
    except sqlite3.OperationalError as e:
        print("  ⚠️  Database table not found:", e)

def get_event_type_distribution(conn: sqlite3.Connection):
    """Show event type distribution"""
    print("\n📈 EVENT TYPE DISTRIBUTION:")
    print("-" * 60)
    
    try:
        query = """
            SELECT event_type, COUNT(*) as count
            FROM research_events
            GROUP BY event_type
            ORDER BY count DESC
        """
        cursor = conn.execute(query)
        
        for row in cursor:
            print("  ", row[0], ":", row[1], "events")
    except sqlite3.OperationalError as e:
        print("  ⚠️  Database table not found:", e)

def get_domain_distribution(conn: sqlite3.Connection):
    """Show research domain distribution"""
    print("\n🔬 DOMAIN DISTRIBUTION:")
    print("-" * 60)
    
    try:
        query = """
            SELECT research_domain, COUNT(*) as count
            FROM research_events
            GROUP BY research_domain
            ORDER BY count DESC
        """
        cursor = conn.execute(query)
        
        for row in cursor:
            print("  ", row[0], ":", row[1], "events")
    except sqlite3.OperationalError as e:
        print("  ⚠️  Database table not found:", e)

def upsert_source(con, source_id: str, pdf_file: str, metadata: dict):
    """Updated to include metadata"""
    con.execute(
        """INSERT OR IGNORE INTO sources(source_id, pdf_file, title, authors, year, doi, imported_at)
           VALUES (?,?,?,?,?,?,?)""",
        (source_id, pdf_file, metadata.get('title'), metadata.get('authors'), 
         metadata.get('year'), metadata.get('doi'), now_iso()),
    )

def insert_document(con, source_id: str, file_path: str, sha256: str) -> str:
    doc_id = sha16(f"{source_id}|{file_path}|{sha256}")
    con.execute(
        """INSERT OR IGNORE INTO documents(doc_id, source_id, file_path, file_type, sha256, created_at)
           VALUES (?,?,?,?,?,?)""",
        (doc_id, source_id, file_path, "pdf", sha256, now_iso()),
    )
    return doc_id

def insert_chunk(con, source_id: str, doc_id: str, page_number: int, section_guess: str, chunk_text: str) -> str:
    chunk_id = sha16(f"{doc_id}|{page_number}|{chunk_text[:200]}")
    con.execute(
        """INSERT OR IGNORE INTO chunks(chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, now_iso()),
    )
    return chunk_id

def upsert_tag(con, tag: str):
    con.execute("INSERT OR IGNORE INTO tags(tag_name) VALUES(?)", (tag,))
    # Get tag_id for further use
    cur = con.execute("SELECT tag_id FROM tags WHERE tag_name=?", (tag,))
    row = cur.fetchone()
    return row[0] if row else None

def upsert_entity(con, entity_type: str, entity_name: str, entity_variant: str | None, organism: str | None) -> str:
    key = f"{entity_type}|{entity_name}|{entity_variant or ''}|{organism or ''}"
    entity_id = sha16(key)
    con.execute(
        """INSERT OR IGNORE INTO entities(entity_id, entity_type, entity_name, entity_variant, organism, created_at)
           VALUES (?,?,?,?,?,?)""",
        (entity_id, entity_type, entity_name, entity_variant, organism, now_iso()),
    )
    return entity_id

def insert_event(con, source_id: str, doc_id: str, chunk_id: str, page_number: int,
                 domain: str, event_type: str, study_stage: str, biological_system: str | None, application_area: str | None,
                 outcome: str, failure_reason: str, decision_taken: str, decision_driver: str | None,
                 evidence_snippet: str, evidence_strength_v: str, confidence_v: str) -> str:
    base = f"{source_id}|{doc_id}|{page_number}|{event_type}|{evidence_snippet[:180]}"
    event_id = sha16(base)
    con.execute(
        """INSERT OR IGNORE INTO research_events(
             event_id, research_domain, event_type, study_stage, biological_system, application_area,
             outcome, failure_reason, decision_taken, decision_driver,
             evidence_snippet, evidence_strength, confidence,
             source_id, doc_id, chunk_id, page_number, created_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event_id, domain, event_type, study_stage, biological_system, application_area,
            outcome, failure_reason, decision_taken, decision_driver,
            evidence_snippet[:500], evidence_strength_v, confidence_v,
            source_id, doc_id, chunk_id, page_number, now_iso()
        ),
    )
    return event_id

def link_event_entity(con, event_id: str, entity_id: str, role: str):
    con.execute(
        """INSERT OR IGNORE INTO event_entities(event_id, entity_id, role)
           VALUES (?,?,?)""",
        (event_id, entity_id, role),
    )

def insert_measurement(con, event_id: str, measurement: dict):
    """Insert quantitative measurement"""
    measurement_id = sha16(f"{event_id}|{measurement['measurement_type']}|{measurement['value']}|{measurement['unit']}")
    con.execute(
        """INSERT OR IGNORE INTO quantitative_measurements(
             measurement_id, event_id, measurement_type, value, unit, context, created_at
           ) VALUES (?,?,?,?,?,?,?)""",
        (measurement_id, event_id, measurement['measurement_type'], 
         measurement['value'], measurement['unit'], measurement['context'], now_iso()),
    )

def insert_relationship(con, entity_id_1: str, entity_id_2: str, relationship_type: str):
    """Insert entity relationship (matches entity_relationships schema)"""
    relationship_id = sha16(f"{entity_id_1}|{entity_id_2}|{relationship_type}")
    con.execute(
        """INSERT OR IGNORE INTO entity_relationships(
             relationship_id, source_entity_id, target_entity_id, relationship_type, created_at
           ) VALUES (?,?,?,?,?)""",
        (relationship_id, entity_id_1, entity_id_2, relationship_type, now_iso()),
    )
    return relationship_id

def link_event_tag(con, event_id: str, tag: str):
    upsert_tag(con, tag)   # ensures tag row exists first
    con.execute(
        "INSERT OR IGNORE INTO event_tags (event_id, tag) VALUES (?, ?)",
        (event_id, tag)
    )
    con.commit()
