
-- DEPRECATED: This file is no longer canonical.
-- The canonical schema is now at the project root: ../schema.sql

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

-- Indexes to speed up foreign key lookups (must come after table creation)
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_source_id ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_research_events_source_id ON research_events(source_id);
CREATE INDEX IF NOT EXISTS idx_research_events_doc_id ON research_events(doc_id);
CREATE INDEX IF NOT EXISTS idx_research_events_chunk_id ON research_events(chunk_id);
CREATE INDEX IF NOT EXISTS idx_event_entities_entity_id ON event_entities(entity_id);
CREATE INDEX IF NOT EXISTS idx_quantitative_measurements_event_id ON quantitative_measurements(event_id);
