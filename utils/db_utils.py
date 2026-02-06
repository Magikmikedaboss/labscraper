"""Shared utilities for database inspection"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

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
    
    # Safely quote the table name for use in SQL
    safe_table = f'"{table.replace('"', '""')}"'
    
    cursor = conn.execute(f"SELECT COUNT(*) FROM {safe_table}")
    count = cursor.fetchone()[0]
    
    cursor = conn.execute(f"PRAGMA table_info({safe_table})")
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
    print(f"\n📚 TOP SOURCES (by event count):")
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
