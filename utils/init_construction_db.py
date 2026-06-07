"""
Initialize peptide_intel_construction.sqlite schema for construction_science pipeline.
Run this script once before running the PDF scraper if the DB is missing tables.
"""
import sqlite3
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    pdf_file TEXT,
    title TEXT,
    authors TEXT,
    year INTEGER,
    doi TEXT,
    imported_at TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    source_id TEXT,
    file_path TEXT,
    file_type TEXT,
    sha256 TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT,
    source_id TEXT,
    page_number INTEGER,
    section_guess TEXT,
    chunk_text TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT,
    entity_name TEXT,
    entity_variant TEXT,
    organism TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS research_events (
    event_id TEXT PRIMARY KEY,
    research_domain TEXT,
    event_type TEXT,
    stage TEXT,
    system_context TEXT,
    application_context TEXT,
    outcome TEXT,
    failure_reason TEXT,
    decision_taken TEXT,
    decision_driver TEXT,
    evidence_snippet TEXT,
    evidence_strength TEXT,
    confidence TEXT,
    source_id TEXT,
    doc_id TEXT,
    chunk_id TEXT,
    page_number INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS event_entities (
    event_id TEXT,
    entity_id TEXT,
    role TEXT,
    PRIMARY KEY (event_id, entity_id, role),
    FOREIGN KEY (event_id) REFERENCES research_events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS entity_relationships (
    -- Stores directed relationships between entities via source_entity_id and target_entity_id.
    -- Typical relationship_type values include parent_of, related_to, and derived_from.
    -- FOREIGN KEYs use ON DELETE CASCADE, so removing an entity also removes inbound and outbound links and can affect graph integrity.
    relationship_id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    target_entity_id TEXT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    context TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_entity_relationships_source
    ON entity_relationships(source_entity_id);

CREATE INDEX IF NOT EXISTS idx_entity_relationships_target
    ON entity_relationships(target_entity_id);

CREATE TABLE IF NOT EXISTS tags (
    tag TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS event_tags (
    event_id TEXT,
    tag TEXT,
    PRIMARY KEY (event_id, tag)
);

CREATE TABLE IF NOT EXISTS quantitative_measurements (
    measurement_id TEXT PRIMARY KEY,
    event_id TEXT,
    measurement_type TEXT,
    value REAL,
    unit TEXT,
    context TEXT,
    created_at TEXT
);
'''

def main():
    db_path = Path("output/peptide_intel_construction.sqlite")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA)
        con.commit()
        print(f"✅ Initialized schema in {db_path.resolve()}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
