import sqlite3

from pathlib import Path

DB_PATH = Path('runs/test_construction_fix.sqlite')

def main():
    if not DB_PATH.exists():
        print(f"❌ Database file not found: {DB_PATH}")
        return

    # Use context manager for database connection
    with sqlite3.connect(DB_PATH) as con:
        tables = [t[0] for t in con.execute('SELECT name FROM sqlite_master WHERE type="table"')]
        print('Tables:', tables)

        # Check if entities table exists and has data
        if 'entities' in tables:
            count = con.execute('SELECT COUNT(*) FROM entities').fetchone()[0]
            print(f'Entities count: {count}')
            
            # Show some example entities
            entities = con.execute('SELECT entity_type, entity_name, entity_variant FROM entities LIMIT 10').fetchall()
            print('Sample entities:')
            for entity_type, name, variant in entities:
                print(f'  {entity_type}: {name} ({variant})')

        # Check chunks table
        if 'chunks' in tables:
            count = con.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
            print(f'Chunks count: {count}')
            
            # Check column names
            columns = [c[1] for c in con.execute('PRAGMA table_info(chunks)')]
            print(f'Chunks columns: {columns}')
            
            # Show some example chunks
            if 'chunk_text' in columns:
                chunks = con.execute('SELECT chunk_text FROM chunks LIMIT 5').fetchall()
                print('Sample chunks:')
                for i, (chunk_text,) in enumerate(chunks):
                    preview = (chunk_text[:100] if chunk_text else '<NULL>')
                    print(f'  Chunk {i+1}: {preview}...')
        # Check documents table
        if 'documents' in tables:
            count = con.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
            print(f'Documents count: {count}')

if __name__ == "__main__":
    main()
