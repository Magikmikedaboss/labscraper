-- Schema initialization for labscraper
-- Enable foreign key enforcement
PRAGMA foreign_keys = ON;
-- Indexes to speed up foreign key lookups
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_source_id ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_research_events_source_id ON research_events(source_id);
CREATE INDEX IF NOT EXISTS idx_research_events_doc_id ON research_events(doc_id);
CREATE INDEX IF NOT EXISTS idx_research_events_chunk_id ON research_events(chunk_id);
CREATE INDEX IF NOT EXISTS idx_event_entities_entity_id ON event_entities(entity_id);
CREATE INDEX IF NOT EXISTS idx_quantitative_measurements_event_id ON quantitative_measurements(event_id);
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    pdf_file TEXT NOT NULL,
    title TEXT,
    authors TEXT,
    year INTEGER,
    doi TEXT,
    imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources (source_id)
);

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
);

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
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    entity_variant TEXT,
    organism TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_entities (
    event_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    role TEXT,
    PRIMARY KEY (event_id, entity_id),
    FOREIGN KEY (event_id) REFERENCES research_events (event_id),
    FOREIGN KEY (entity_id) REFERENCES entities (entity_id)
);

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
);

CREATE TABLE IF NOT EXISTS tags (
    tag TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS event_tags (
    event_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (event_id, tag),
    FOREIGN KEY (event_id) REFERENCES research_events (event_id),
    FOREIGN KEY (tag) REFERENCES tags (tag)
);

CREATE TABLE IF NOT EXISTS quantitative_measurements (
    measurement_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    measurement_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    context TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES research_events (event_id)
);
