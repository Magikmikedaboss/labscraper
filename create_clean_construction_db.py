#!/usr/bin/env python3
"""
Create a clean construction science database by extracting only construction domain data
"""
import sqlite3
from pathlib import Path

def create_clean_construction_db():
    # Create clean database
    clean_db = Path("db/construction_science_clean.sqlite")
    clean_db.parent.mkdir(exist_ok=True)
    
    # Copy schema from original
    original_db = Path("db/runs.sqlite")
    
    # Precondition check: verify original database exists
    if not original_db.exists():
        raise SystemExit(f"❌ Original database not found: {original_db}")
    
    # Create new database by copying schema from original database
    with sqlite3.connect(original_db) as old_conn, sqlite3.connect(clean_db) as new_conn:
        # Copy schema from original database
        for line in old_conn.iterdump():
            if line.startswith('CREATE TABLE') or line.startswith('CREATE INDEX'):
                try:
                    new_conn.execute(line)
                except sqlite3.Error as e:
                    print(f"Warning: Could not execute schema line: {line[:100]}... Error: {e}")
        
        new_conn.commit()
    
    # Extract construction data from original database
    with sqlite3.connect(original_db) as old_conn, sqlite3.connect(clean_db) as new_conn:
        # Get construction events
        construction_events = old_conn.execute(
            "SELECT event_id, research_domain, event_type, study_stage, biological_system, application_area, outcome, failure_reason, decision_taken, decision_driver, evidence_snippet, evidence_strength, confidence, source_id, doc_id, chunk_id, page_number, created_at FROM research_events WHERE research_domain = 'construction'"
        ).fetchall()
        
        print(f"Found {len(construction_events)} construction events")
        
        # Sources
        sources = old_conn.execute(
            "SELECT source_id, pdf_file, title, authors, year, doi, venue, imported_at FROM sources WHERE source_id IN (SELECT DISTINCT source_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Documents
        documents = old_conn.execute(
            "SELECT doc_id, source_id, file_path, file_type, sha256, created_at FROM documents WHERE doc_id IN (SELECT DISTINCT doc_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Chunks
        chunks = old_conn.execute(
            "SELECT chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, created_at FROM chunks WHERE chunk_id IN (SELECT DISTINCT chunk_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Entities
        entities = old_conn.execute(
            "SELECT entity_id, entity_type, entity_name, entity_variant, organism, created_at FROM entities WHERE entity_id IN (SELECT DISTINCT entity_id FROM event_entities WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction'))"
        ).fetchall()
        
        # Event entities
        event_entities = old_conn.execute(
            "SELECT event_id, entity_id, role FROM event_entities WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Event tags
        event_tags = old_conn.execute(
            "SELECT event_id, tag FROM event_tags WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Measurements
        measurements = old_conn.execute(
            "SELECT measurement_id, event_id, measurement_type, value, unit, context, created_at FROM quantitative_measurements WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction')"
        ).fetchall()
        
        # Relationships (check if table exists first)
        try:
            relationships = old_conn.execute(
                "SELECT relationship_id, entity_id_1, entity_id_2, relationship_type, event_id, confidence, created_at FROM entity_relationships WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction')"
            ).fetchall()
        except sqlite3.OperationalError:
            relationships = []
        
        # Tags
        tags = old_conn.execute(
            "SELECT tag FROM tags WHERE tag IN (SELECT DISTINCT tag FROM event_tags WHERE event_id IN (SELECT event_id FROM research_events WHERE research_domain = 'construction'))"
        ).fetchall()
        
        # Insert data into new database
        print("Inserting data into clean database...")
        
        # Insert sources with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO sources 
            (source_id, pdf_file, title, authors, year, doi, venue, imported_at) 
            VALUES (?,?,?,?,?,?,?,?)
        """, sources)
        
        # Insert documents with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO documents 
            (doc_id, source_id, file_path, file_type, sha256, created_at) 
            VALUES (?,?,?,?,?,?)
        """, documents)
        
        # Insert chunks with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO chunks 
            (chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, created_at) 
            VALUES (?,?,?,?,?,?,?)
        """, chunks)
        
        # Insert entities with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO entities 
            (entity_id, entity_type, entity_name, entity_variant, organism, created_at) 
            VALUES (?,?,?,?,?,?)
        """, entities)
        
        # Insert events with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO research_events 
            (event_id, research_domain, event_type, study_stage, biological_system, application_area, 
             outcome, failure_reason, decision_taken, decision_driver, evidence_snippet, 
             evidence_strength, confidence, source_id, doc_id, chunk_id, page_number, created_at) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, construction_events)
        
        # Insert event entities with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO event_entities 
            (event_id, entity_id, role) 
            VALUES (?,?,?)
        """, event_entities)
        
        # Insert event tags with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO event_tags 
            (event_id, tag) 
            VALUES (?,?)
        """, event_tags)
        
        # Insert measurements with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO quantitative_measurements 
            (measurement_id, event_id, measurement_type, value, unit, context, created_at) 
            VALUES (?,?,?,?,?,?,?)
        """, measurements)
        
        # Insert relationships with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO entity_relationships 
            (relationship_id, entity_id_1, entity_id_2, relationship_type, event_id, confidence, created_at) 
            VALUES (?,?,?,?,?,?,?)
        """, relationships)
        
        # Insert tags with explicit columns
        new_conn.executemany("""
            INSERT OR IGNORE INTO tags 
            (tag) 
            VALUES (?)
        """, tags)
        
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