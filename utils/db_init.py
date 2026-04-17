"""
utils/db_init.py

Test-only database schema initialization utilities.

This module provides helpers for initializing a test database schema in isolation.

**Do not use for production or persistent database setup.**

For initializing the main db/runs.sqlite database, always use the canonical root-level init_db.py script or its init_db() function.
"""
import os
import sqlite3
from pathlib import Path

def _init_db_schema(db_path):
    """
    Initialize a SQLite database at the given path using the test schema.

    This function is intended **only** for test isolation and should not be used for production or persistent database setup.

    For initializing the main db/runs.sqlite database, always use the canonical root-level init_db.py script or its init_db() function.

    Args:
        db_path (str or Path): Path to the SQLite database file to initialize.
    """
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

    # Block initialization of the canonical persistent DB
    db_path_resolved = Path(db_path).resolve()
    # Compute project root (assume db/ is at project root)
    project_root = Path(__file__).resolve().parents[1]
    canonical_path = (project_root / 'db' / 'runs.sqlite').resolve()
    if db_path_resolved == canonical_path:
        raise ValueError(f"Refusing to initialize canonical persistent DB: {db_path_resolved}")

    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Missing schema.sql at {schema_path}")

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    with sqlite3.connect(db_path) as con:
        con.executescript(schema_sql)
        con.commit()
