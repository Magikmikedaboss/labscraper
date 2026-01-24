import sqlite3

con = sqlite3.connect('output/biohacking_dual_lens.sqlite')
cur = con.cursor()

# Get all tables
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t[0] for t in tables])

# Get schema for each table
for table in tables:
    table_name = table[0]
    print(f"\n{table_name}:")
    schema = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
    for col in schema:
        print(f"  {col[1]} ({col[2]})")

con.close()
