"""
Initialize a test SQLite database with all required tables for CI and local testing.
"""
import sqlite3
from pathlib import Path

def init_test_db(db_path="test.db"):
    # Always use the canonical root-level schema.sql
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema.sql at {schema_path}")
    schema_sql = schema_path.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as con:
        con.executescript(schema_sql)
    print(f"Initialized test DB at {db_path}")

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "test.db"
    init_test_db(db_path)
