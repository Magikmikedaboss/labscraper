
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

def main(argv=None):
    args = sys.argv if argv is None else argv
    if len(args) < 2:
        print("Usage: python check_db_schema.py <database_path>", file=sys.stderr)
        return 1
    try:
        check_db_schema(args[1])
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
