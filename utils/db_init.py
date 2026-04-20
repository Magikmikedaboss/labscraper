"""
utils/db_init.py

Test-only database schema initialization utilities.

This module provides helpers for initializing a test database schema in isolation.

**Do not use for production or persistent database setup.**

For initializing the main db/runs.sqlite database, always use the canonical root-level init_db.py script or its init_db() function.
"""
import sqlite3
from pathlib import Path
from contextlib import closing

def _init_db_schema(db_path):
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

    with closing(sqlite3.connect(db_path)) as con:
        con.executescript(schema_sql)
