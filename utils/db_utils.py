"""Shared utilities for database inspection"""

from difflib import SequenceMatcher
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.common import now_iso, sha16


def db_has_all_tables(con, required_tables=None):
    """Check if all required tables exist in the database connection."""
    if required_tables is None:
        required_tables = [
            "sources", "documents", "chunks", "entities", "research_events",
            "event_entities", "event_tags", "quantitative_measurements", "entity_relationships", "tags"
        ]
    cursor = con.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {row[0] for row in cursor.fetchall()}
        return all(t in existing for t in required_tables)
    finally:
        cursor.close()


logger = logging.getLogger(__name__)
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
    try:
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()

def get_table_stats(conn: sqlite3.Connection, table: str) -> Dict:
    """Get row count and columns for a table"""
    # First validate that the table exists to prevent SQL injection
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    try:
        existing_tables = [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
    
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
    try:
        count = cursor.fetchone()[0]
    finally:
        cursor.close()

    pragma_query = 'PRAGMA table_info("{}")'.format(table)
    cursor = conn.execute(pragma_query)
    try:
        columns = [row[1] for row in cursor.fetchall()]
    finally:
        cursor.close()

    return {'count': count, 'columns': columns}

def inspect_database(db_path: str = 'db/runs.sqlite', detailed: bool = False):
    """
    Inspect database contents
    
    Args:
        db_path: Path to SQLite database
        detailed: If True, show detailed stats for each table
    """
    logger.info('\n%s', '='*60)
    logger.info('DATABASE INSPECTION: %s', db_path)
    logger.info('%s\n', '='*60)
    result = {"db_path": db_path, "tables": []}
    try:
        conn = connect_db(db_path)
        tables = get_tables(conn)
        result["tables"] = tables
        logger.info("📊 Tables found: %d", len(tables))
        logger.info("")
        for table in tables:
            stats = get_table_stats(conn, table)
            logger.info("📋 %s", table)
            logger.info("   Rows: %s", f"{stats['count']:,}")
            if detailed:
                logger.info("   Columns: %s", ', '.join(stats['columns']))
            logger.info("")
        conn.close()
        return result
    except FileNotFoundError as e:
        logger.error("❌ %s", e)
        return result
    except sqlite3.Error as e:
        logger.error("❌ Database error: %s", e)
        return result

def show_recent_events(conn: sqlite3.Connection, limit: int = 5):
    """Show recent research events"""
    logger.info("\n📰 RECENT EVENTS (last %d):", limit)
    logger.info("-" * 60)
    
    try:
        query = """
            SELECT event_type, research_domain, confidence, created_at
            FROM research_events
            ORDER BY created_at DESC
            LIMIT ?
        """
        cursor = conn.execute(query, (limit,))
        try:
            for row in cursor:
                confidence = row[2] if row[2] is not None else "unknown"
                logger.info("  • %s | %s | confidence: %s", row[0], row[1], confidence)
                logger.info("    %s", row[3])
                logger.info("")
        finally:
            cursor.close()
    except sqlite3.OperationalError as e:
        logger.error("  ⚠️  Database table not found: %s", e)

def show_top_sources(conn: sqlite3.Connection, limit: int = 5):
    """Show sources with most events"""
    logger.info("\n📚 TOP SOURCES (by event count):")
    logger.info("-" * 60)
    
    try:
        query = """
            SELECT s.source_id, s.title, COUNT(re.event_id) as event_count
            FROM sources s
            LEFT JOIN research_events re ON s.source_id = re.source_id
            GROUP BY s.source_id
            ORDER BY event_count DESC
            LIMIT ?
        """
        cursor = None
        try:
            cursor = conn.execute(query, (limit,))
            for row in cursor:
                logger.info("  %s", row[1])
                logger.info("    Events: %s", row[2])
                logger.info("")
        finally:
            if cursor is not None:
                cursor.close()
    except sqlite3.OperationalError as e:
        logger.error("  ⚠️  Database table not found: %s", e)

def show_pdf_cache(cache_dir: str = 'input/rss_cache'):
    """Show PDF cache contents"""
    cache_dir = Path(cache_dir)
    
    logger.info("\n📁 PDF CACHE:")
    logger.info("-" * 60)
    

    if not cache_dir.exists():
        logger.error("  ⚠️  Cache directory not found")
        return

    # Enumerate files in the cache directory and log their details
    for f in cache_dir.iterdir():
        if f.is_file():
            st = f.stat()
            mod_time = datetime.fromtimestamp(st.st_mtime).isoformat(sep=' ', timespec='seconds')
            logger.info("  %s | %d bytes | modified: %s", f.name, st.st_size, mod_time)

def get_entity_distribution(conn: sqlite3.Connection):
    """Show entity distribution across types"""
    logger.info("\n🏗️  ENTITY DISTRIBUTION:")
    logger.info("-" * 60)
    
    cursor = None
    try:
        query = """
            SELECT entity_type, COUNT(*) as count
            FROM entities
            GROUP BY entity_type
            ORDER BY count DESC
        """
        cursor = conn.execute(query)
        for row in cursor:
            logger.info("  %s : %s entities", row[0], row[1])
    except sqlite3.OperationalError as e:
        logger.error("  ⚠️  Database table not found: %s", e)
    finally:
        if cursor is not None:
            cursor.close()

def get_event_type_distribution(conn: sqlite3.Connection):
    """Show event type distribution"""
    logger.info("\n📈 EVENT TYPE DISTRIBUTION:")
    logger.info("-" * 60)
    
    cursor = None
    try:
        query = """
            SELECT event_type, COUNT(*) as count
            FROM research_events
            GROUP BY event_type
            ORDER BY count DESC
        """
        cursor = conn.execute(query)
        for row in cursor:
            logger.info("  %s : %s events", row[0], row[1])
    except sqlite3.OperationalError as e:
        logger.error("  ⚠️  Database table not found: %s", e)
    finally:
        if cursor is not None:
            cursor.close()

def get_domain_distribution(conn: sqlite3.Connection):
    """Show research domain distribution"""
    logger.info("\n🔬 DOMAIN DISTRIBUTION:")
    logger.info("-" * 60)
    
    cursor = None
    try:
        query = """
            SELECT research_domain, COUNT(*) as count
            FROM research_events
            GROUP BY research_domain
            ORDER BY count DESC
        """
        cursor = conn.execute(query)
        for row in cursor:
            logger.info("  %s : %s events", row[0], row[1])
    except sqlite3.OperationalError as e:
        logger.error("  ⚠️  Database table not found: %s", e)
    finally:
        if cursor is not None:
            cursor.close()

def _normalize_text(value: Any) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().lower().split())


def _normalize_doi(value: Any) -> str:
    doi = _normalize_text(value)
    if not doi:
        return ""
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
            break
    return doi.strip("/ ")


def _table_columns(con: sqlite3.Connection, table_name: str) -> set[str]:
    rows = con.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _ensure_source_tracking_schema(con: sqlite3.Connection) -> None:
    columns = _table_columns(con, "sources")
    if "publication_date" not in columns:
        con.execute("ALTER TABLE sources ADD COLUMN publication_date TEXT")
    if "domain" not in columns:
        con.execute("ALTER TABLE sources ADD COLUMN domain TEXT")
    con.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_sources_doi
        ON sources(doi)
        WHERE doi IS NOT NULL AND trim(doi) <> ''
        """
    )
    con.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_documents_sha256
        ON documents(sha256)
        WHERE sha256 IS NOT NULL AND trim(sha256) <> ''
        """
    )


def _resolve_existing_source_id(con: sqlite3.Connection, source_id: str, metadata: dict) -> str:
    doi = _normalize_doi(metadata.get("doi"))
    if doi:
        row = con.execute(
            """
            SELECT source_id
            FROM sources
            WHERE lower(trim(replace(replace(replace(replace(replace(doi,
                'https://doi.org/', ''),
                'http://doi.org/', ''),
                'https://dx.doi.org/', ''),
                'http://dx.doi.org/', ''),
                'doi:', ''))) = ?
            LIMIT 1
            """,
            (doi,),
        ).fetchone()
        if row:
            return row[0]

    title = _normalize_text(metadata.get("title"))
    if not title:
        return source_id

    exact = con.execute(
        "SELECT source_id FROM sources WHERE lower(trim(title)) = ? LIMIT 1",
        (title,),
    ).fetchone()
    if exact:
        return exact[0]

    candidates = con.execute(
        "SELECT source_id, title FROM sources WHERE title IS NOT NULL LIMIT 1000"
    ).fetchall()
    for candidate_id, candidate_title in candidates:
        if not candidate_title:
            continue
        score = SequenceMatcher(None, title, _normalize_text(candidate_title)).ratio()
        if score >= 0.97:
            return candidate_id

    return source_id


def upsert_source(con: sqlite3.Connection, source_id: str, pdf_file: str, metadata: dict) -> str:
    """Upsert source with provenance metadata and DOI/title dedup checks."""
    _ensure_source_tracking_schema(con)
    metadata = metadata or {}
    source_id = _resolve_existing_source_id(con, source_id, metadata)

    authors = metadata.get("authors")
    if isinstance(authors, (list, tuple)):
        authors = ", ".join(str(a) for a in authors if a)

    year = metadata.get("year")
    if isinstance(year, str) and year.isdigit():
        year = int(year)

    publication_date = metadata.get("publication_date")
    if not publication_date and year:
        publication_date = str(year)

    values = {
        "source_id": source_id,
        "pdf_file": pdf_file,
        "title": metadata.get("title"),
        "authors": authors,
        "year": year,
        "publication_date": publication_date,
        "venue": metadata.get("venue") or metadata.get("journal"),
        "doi": _normalize_doi(metadata.get("doi")) or None,
        "url": metadata.get("url"),
        "domain": metadata.get("domain"),
        "imported_at": now_iso(),
    }

    source_columns = _table_columns(con, "sources")
    insert_cols = [k for k in values if k in source_columns]
    placeholders = ",".join("?" for _ in insert_cols)
    update_cols = [k for k in insert_cols if k != "source_id"]
    update_sql = ", ".join(f"{k}=excluded.{k}" for k in update_cols)
    params = tuple(values[col] for col in insert_cols)

    con.execute(
        f"""
        INSERT INTO sources({','.join(insert_cols)})
        VALUES ({placeholders})
        ON CONFLICT(source_id) DO UPDATE SET {update_sql}
        """,
        params,
    )
    return source_id

def insert_document(con, source_id: str, file_path: str, sha256: str) -> str:
    if sha256:
        existing = con.execute(
            "SELECT doc_id FROM documents WHERE sha256 = ? LIMIT 1",
            (sha256,),
        ).fetchone()
        if existing:
            return existing[0]

    doc_id = sha16(sha256 or f"{source_id}|{file_path}")
    con.execute(
        """INSERT OR IGNORE INTO documents(doc_id, source_id, file_path, file_type, sha256, created_at)
           VALUES (?,?,?,?,?,?)""",
        (doc_id, source_id, file_path, "pdf", sha256, now_iso()),
    )
    return doc_id

def insert_chunk(con, source_id: str, doc_id: str, page_number: int, section_guess: str, chunk_text: str) -> str:
    # Use full chunk text to avoid collisions from identical prefixes.
    chunk_id = sha16(f"{doc_id}|{page_number}|{chunk_text}")
    con.execute(
        """INSERT OR IGNORE INTO chunks(chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, now_iso()),
    )
    return chunk_id
def upsert_tag(con, tag: str) -> str:
    con.execute("INSERT OR IGNORE INTO tags(tag) VALUES(?)", (tag,))
    return tag

def upsert_entity(con, entity_type: str, entity_name: str, entity_variant: Optional[str], organism: Optional[str]) -> str:
    key = f"{entity_type}|{entity_name}|{entity_variant or ''}|{organism or ''}"
    entity_id = sha16(key)
    con.execute(
        """INSERT OR IGNORE INTO entities(entity_id, entity_type, entity_name, entity_variant, organism, created_at)
           VALUES (?,?,?,?,?,?)""",
        (entity_id, entity_type, entity_name, entity_variant, organism, now_iso()),
    )
    return entity_id

def insert_event(
    *,
    con,
    source_id: str,
    doc_id: str,
    chunk_id: str,
    page_number: int,
    domain: str,
    event_type: str,
    study_stage: str,
    biological_system: Optional[str],
    application_area: Optional[str],
    outcome: str,
    failure_reason: str,
    decision_taken: str,
    decision_driver: Optional[str],
    evidence_snippet: str,
    evidence_strength_v: str,
    confidence_v: str,
) -> str:
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
    """Insert quantitative measurement. Tolerates missing fields and raises ValueError for required ones."""
    mtype = measurement.get('measurement_type')
    value = measurement.get('value')
    unit = measurement.get('unit')
    context = measurement.get('context', None)
    # measurement_type, value, and unit are required for a valid measurement
    if mtype is None or value is None or unit is None:
        raise ValueError(f"Missing required measurement fields: measurement_type={mtype}, value={value}, unit={unit}")
    measurement_id = sha16(f"{event_id}|{mtype}|{value}|{unit}")
    con.execute(
        """INSERT OR IGNORE INTO quantitative_measurements(
             measurement_id, event_id, measurement_type, value, unit, context, created_at
           ) VALUES (?,?,?,?,?,?,?)""",
        (measurement_id, event_id, mtype, value, unit, context, now_iso()),
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


def _db_has_all_tables(db_path: Path) -> bool:
    """Check if all required tables exist in the DB."""
    required_tables = {
        "sources",
        "documents",
        "chunks",
        "entities",
        "research_events",
        "event_entities",
        "tags",
        "event_tags",
        "quantitative_measurements",
        "entity_relationships",
    }
    try:
        with sqlite3.connect(db_path, timeout=30.0) as con:
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = {t[0] for t in tables}
            return required_tables.issubset(table_names)
    except Exception:
        return False
