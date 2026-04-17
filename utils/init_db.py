"""
Initialize the main db.sqlite database using the schema.sql file.
"""
import sqlite3
from pathlib import Path
import os

def main(db_path="db.sqlite"):
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    schema_sql = schema_path.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as con:
        con.executescript(schema_sql)
        con.commit()
    print(f"Initialized database at {db_path}")

if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "db.sqlite"
    main(db_path)
