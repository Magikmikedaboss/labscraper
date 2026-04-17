"""
Initialize a test SQLite database with all required tables for CI and local testing.
"""
import sqlite3
from pathlib import Path

def init_test_db(db_path="test.db"):
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema.sql at {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with sqlite3.connect(db_path) as con:
        con.executescript(schema_sql)
    print(f"Initialized test DB at {db_path}")

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "test.db"
    init_test_db(db_path)
