#!/usr/bin/env python3
import sqlite3
import os

# Create database and initialize schema
db_path = 'db/runs.sqlite'
os.makedirs(os.path.dirname(db_path), exist_ok=True)

with sqlite3.connect(db_path) as conn:
    with open('output/peptide_intel_schema.sql', 'r') as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    print('Database schema initialized successfully')

# Verify tables were created
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables created:', [t[0] for t in tables])