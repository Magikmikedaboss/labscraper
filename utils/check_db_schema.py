
import sqlite3
import sys

def check_db_schema(db_path):
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print("Tables:", [t[0] for t in tables])
        for table in tables:
            table_name = table[0]
            print(f"\n{table_name}:")
            schema = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
            for col in schema:
                print(f"  {col[1]} ({col[2]})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_db_schema.py <database_path>", file=sys.stderr)
        sys.exit(1)
    try:
        check_db_schema(sys.argv[1])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
