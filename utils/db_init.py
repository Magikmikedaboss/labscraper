"""
utils/db_init.py

Test-only database schema initialization utilities.

This module provides helpers for initializing a test database schema in isolation.

**Do not use for production or persistent database setup.**

For initializing the main db/runs.sqlite database, always use the canonical root-level init_db.py script or its init_db() function.
"""
import sqlite3
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def ensure_research_events_columns_renamed(con: sqlite3.Connection) -> None:
    """Rename legacy research_events context columns only when needed."""
    columns = {
        row[1]
        for row in con.execute("PRAGMA table_info(research_events)").fetchall()
    }
    legacy_cols = {"study_stage", "biological_system", "application_area"}
    target_cols = {"stage", "system_context", "application_context"}

    should_apply = legacy_cols.issubset(columns) and target_cols.isdisjoint(columns)
    if should_apply:
        con.executescript(
            """
            ALTER TABLE research_events RENAME COLUMN study_stage TO stage;
            ALTER TABLE research_events RENAME COLUMN biological_system TO system_context;
            ALTER TABLE research_events RENAME COLUMN application_area TO application_context;
            """
        )
        logger.info("Applied migration: 01_rename_research_event_context_columns.sql")
    else:
        logger.debug("Skipped migration 01_rename_research_event_context_columns.sql due to current research_events column set")

def init_db_schema(db_path):
    """
    Initialize a SQLite database at the given path using the test schema.

    This function is intended **only** for test isolation and should not be used for production or persistent database setup.

    For initializing the main db/runs.sqlite database, always use the canonical root-level init_db.py script or its init_db() function.

    Args:
        db_path (str or Path): Path to the SQLite database file to initialize.
    """
    # Always use the canonical root-level schema.sql

    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / 'schema.sql'

    # Block initialization of the canonical persistent DB
    db_path_resolved = Path(db_path).resolve()
    canonical_path = (project_root / 'db' / 'runs.sqlite').resolve()
    if db_path_resolved == canonical_path:
        raise RuntimeError(f"Refusing to initialize canonical persistent DB: {db_path_resolved}")

    db_path_resolved.parent.mkdir(parents=True, exist_ok=True)

    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema.sql at {schema_path}")

    schema_sql = schema_path.read_text(encoding='utf-8')

    with sqlite3.connect(db_path_resolved) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(schema_sql)
        ensure_research_events_columns_renamed(con)


# Backward-compatible alias for any external imports.
_init_db_schema = init_db_schema
