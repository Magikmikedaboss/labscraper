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


def _apply_rename_context_columns_migration_if_needed(con: sqlite3.Connection, project_root: Path) -> None:
    """Apply migration 01 only when legacy context columns are present."""
    migration_path = project_root / "migrations" / "01_rename_research_event_context_columns.sql"
    if not migration_path.exists():
        return

    columns = {
        row[1]
        for row in con.execute("PRAGMA table_info(research_events)").fetchall()
    }
    legacy_cols = {"study_stage", "biological_system", "application_area"}
    target_cols = {"stage", "system_context", "application_context"}

    should_apply = legacy_cols.issubset(columns) and target_cols.isdisjoint(columns)
    if should_apply:
        con.executescript(migration_path.read_text(encoding="utf-8"))
        logger.info("Applied migration: %s", migration_path.name)
    else:
        logger.debug("Skipped migration %s due to current research_events column set", migration_path.name)

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
        raise ValueError(f"Refusing to initialize canonical persistent DB: {db_path_resolved}")

    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema.sql at {schema_path}")

    schema_sql = schema_path.read_text(encoding='utf-8')

    with sqlite3.connect(db_path_resolved) as con:
        con.executescript(schema_sql)
        _apply_rename_context_columns_migration_if_needed(con, project_root)


# Backward-compatible alias for any external imports.
_init_db_schema = init_db_schema
