"""
Initialize the main db.sqlite database using the schema.sql file.

Foreign key enforcement:
- The main() function in this module enables PRAGMA foreign_keys when initializing the database from schema.sql.
- For all other database usage, downstream callers should use get_connection_with_foreign_keys(db_path) to obtain a connection with foreign key enforcement enabled.
"""

import sqlite3
import argparse
import sys
from pathlib import Path


def get_connection_with_foreign_keys(db_path):
    """
    Return a sqlite3.Connection to db_path with PRAGMA foreign_keys enabled.
    Use this in downstream code to ensure foreign key constraints are enforced.
    """
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def main(db_path="db.sqlite", force=False):
    # Always use the canonical root-level schema.sql
    project_root = Path(__file__).resolve().parents[1]
    canonical_db_path = (project_root / "db" / "runs.sqlite").resolve()
    db_path_resolved = Path(db_path).resolve()
    if not force and db_path_resolved == canonical_db_path:
        raise RuntimeError(f"Refusing to initialize the canonical root DB at {canonical_db_path}. Choose a different path, use --force to override, or modify this guardrail if intentional.")
    schema_path = project_root / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    schema_sql = schema_path.read_text(encoding="utf-8")
    with sqlite3.connect(db_path_resolved) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(schema_sql)
    print(f"Initialized database at {db_path_resolved}")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Initialize a SQLite database from schema.sql.")
        parser.add_argument("db_path", nargs="?", default="db.sqlite", help="Path to the database file to initialize.")
        parser.add_argument("--force", action="store_true", help="Allow initializing the canonical db/runs.sqlite path.")
        args = parser.parse_args()
        main(args.db_path, force=args.force)
    except Exception as e:
        print(f"[init_db.py] Error: {e}", file=sys.stderr)
        sys.exit(1)
