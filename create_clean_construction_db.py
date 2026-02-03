#!/usr/bin/env python3
"""
Create a clean construction science database by extracting only construction domain data
"""
import sqlite3
import shutil
from pathlib import Path

def create_clean_construction_db():
    # Create clean database
    clean_db = Path("db/construction_science_clean.sqlite")
    clean_db.parent.mkdir(exist_ok=True)
    
    # Copy schema from original
    original_db = Path("db/runs.sqlite")
    
    # Create new database with schema
    with sqlite3.connect(clean_db) as new_conn:
        # Initialize schema
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                pdf_file TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                year INTEGER,
                doi TEXT,
                venue TEXT,
                imported_at TEXT NOT NULL
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sources (source_id)
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                section_guess TEXT,
                chunk_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id),
                FOREIGN KEY (source_id) REFERENCES sources (source_id)
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS research_events (
                event_id TEXT PRIMARY KEY,
                research_domain TEXT NOT NULL,
                event_type TEXT NOT NULL,
                study_stage TEXT,
                biological_system TEXT,
                application_area TEXT,
                outcome TEXT,
                failure_reason TEXT,
                decision_taken TEXT,
                decision_driver TEXT,
                evidence_snippet TEXT,
                evidence_strength TEXT,
                confidence TEXT,
                source_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sources (source_id),
                FOREIGN KEY (doc_id) REFERENCES documents (doc_id),
                FOREIGN KEY (chunk_id) REFERENCES chunks (chunk_id)
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                entity_variant TEXT,
                organism TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS event_entities (
                event_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                role TEXT,
                PRIMARY KEY (event_id, entity_id),
                FOREIGN KEY (event_id) REFERENCES research_events (event_id),
                FOREIGN KEY (entity_id) REFERENCES entities (entity_id)
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS entity_relationships (
                relationship_id TEXT PRIMARY KEY,
                entity_id_1 TEXT NOT NULL,
                entity_id_2 TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                event_id TEXT,
                confidence TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entity_id_1) REFERENCES entities (entity_id),
                FOREIGN KEY (entity_id_2) REFERENCES entities (entity_id),
                FOREIGN KEY (event_id) REFERENCES research_events (event_id)
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                tag TEXT PRIMARY KEY
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS event_tags (
                event_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (event_id, tag),
                FOREIGN KEY (event_id) REFERENCES research_events (event_id),
                FOREIGN KEY (tag) REFERENCES tags (tag)
            )
        """)
        
        new_conn.execute("""
            CREATE TABLE IF NOT EXISTS quantitative_measurements (
                measurement_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                measurement_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                context TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES research_events (event_id)
            )
        """)
        
        new_conn.commit()
    
    # Extract construction data from original database
    with sqlite3.connect(original_db) as old_conn, sqlite3.connect(clean_db) as new_conn:
        # Get construction events
        construction_events = old_conn.execute(
            "SELECT * FROM research_events WHERE research_domain = 'construction'"
        ).fetchall()
        
        print(f"Found {len(construction_events)} construction events")
        
        # Get related data
        construction_event_ids = [event[0] for event in construction_events]
        
        # Sources
        sources = old_conn.execute(
            "SELECT * FROM sources WHERE source_id IN (SELECT DISTINCT source_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Documents
        documents = old_conn.execute(
            "SELECT * FROM documents WHERE doc_id IN (SELECT DISTINCT doc_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Chunks
        chunks = old_conn.execute(
            "SELECT * FROM chunks WHERE chunk_id IN (SELECT DISTINCT chunk_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Entities
        entities = old_conn.execute(
            "SELECT * FROM entities WHERE entity_id IN (SELECT DISTINCT entity_id FROM event_entities WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction'))"
        ).fetchall()
        
        # Event entities
        event_entities = old_conn.execute(
            "SELECT * FROM event_entities WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Event tags
        event_tags = old_conn.execute(
            "SELECT * FROM event_tags WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Measurements
        measurements = old_conn.execute(
            "SELECT * FROM quantitative_measurements WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Relationships (check if table exists first)
        try:
            relationships = old_conn.execute(
                "SELECT * FROM entity_relationships WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction')"
            ).fetchall()
        except sqlite3.OperationalError:
            relationships = []
        
        # Tags
        tags = old_conn.execute(
            "SELECT * FROM tags WHERE tag IN (SELECT DISTINCT tag FROM event_tags WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction'))"
        ).fetchall()
        
        # Insert data into new database
        print("Inserting data into clean database...")
        
        # Insert sources
        new_conn.executemany("INSERT OR IGNORE INTO sources VALUES (?,?,?,?,?,?,?,?)", sources)
        
        # Insert documents
        new_conn.executemany("INSERT OR IGNORE INTO documents (doc_id, source_id, file_path, file_type, sha256, created_at) VALUES (?,?,?,?,?,?)", documents)
        
        # Insert chunks
        new_conn.executemany("INSERT OR IGNORE INTO chunks VALUES (?,?,?,?,?,?,?)", chunks)
        
        # Insert entities
        new_conn.executemany("INSERT OR IGNORE INTO entities VALUES (?,?,?,?,?,?)", entities)
        
        # Insert events
        new_conn.executemany("INSERT OR IGNORE INTO research_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", construction_events)
        
        # Insert event entities
        new_conn.executemany("INSERT OR IGNORE INTO event_entities VALUES (?,?,?)", event_entities)
        
        # Insert event tags
        new_conn.executemany("INSERT OR IGNORE INTO event_tags VALUES (?,?)", event_tags)
        
        # Insert measurements
        new_conn.executemany("INSERT OR IGNORE INTO quantitative_measurements VALUES (?,?,?,?,?,?,?)", measurements)
        
        # Insert relationships
        new_conn.executemany("INSERT OR IGNORE INTO entity_relationships VALUES (?,?,?,?,?,?,?)", relationships)
        
        # Insert tags
        new_conn.executemany("INSERT OR IGNORE INTO tags VALUES (?)", tags)
        
        new_conn.commit()
    
    print(f"✅ Created clean construction database: {clean_db}")
    
    # Verify the clean database
    with sqlite3.connect(clean_db) as conn:
        cursor = conn.cursor()
        
        print("\n=== CLEAN DATABASE VERIFICATION ===")
        cursor.execute('SELECT DISTINCT research_domain FROM research_events')
        domains = cursor.fetchall()
        print(f"Domains: {[d[0] for d in domains]}")
        
        cursor.execute('SELECT COUNT(*) FROM research_events')
        event_count = cursor.fetchone()[0]
        print(f"Total events: {event_count}")
        
        cursor.execute('SELECT COUNT(*) FROM entities')
        entity_count = cursor.fetchone()[0]
        print(f"Total entities: {entity_count}")
        
        cursor.execute('SELECT DISTINCT entity_type FROM entities')
        entity_types = cursor.fetchall()
        print(f"Entity types: {[e[0] for e in entity_types]}")

if __name__ == "__main__":
    create_clean_construction_db()