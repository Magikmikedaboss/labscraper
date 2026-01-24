import sqlite3
from pathlib import Path

db_path = Path('output/combined_biohacking_all.sqlite')
db_path.parent.mkdir(exist_ok=True)

con = sqlite3.connect(db_path)
con.executescript(open('schema.sql').read())
con.close()

print(f'✅ Database initialized: {db_path}')
