PRAGMA foreign_keys = ON;
-- Added to ensure all foreign key references are valid
CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    title TEXT,
    authors TEXT,
    year INTEGER,
    publication_date TEXT,
    venue TEXT,
    doi TEXT,
    url TEXT,
    domain TEXT,
    pdf_file TEXT,
    imported_at TEXT,
    last_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL DEFAULT 'pdf',
    sha256 TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_sources_doi
ON sources(doi)
WHERE doi IS NOT NULL AND trim(doi) <> '';

CREATE UNIQUE INDEX IF NOT EXISTS uniq_documents_sha256
ON documents(sha256)
WHERE sha256 IS NOT NULL AND trim(sha256) <> '';
CREATE INDEX IF NOT EXISTS idx_sources_year ON sources(year);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    page_number INTEGER,
    section_guess TEXT,
    chunk_text TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE
);

CREATE TRIGGER IF NOT EXISTS trg_chunks_source_id_consistency_insert
BEFORE INSERT ON chunks
FOR EACH ROW
WHEN EXISTS (
    SELECT 1
    FROM documents d
    WHERE d.doc_id = NEW.doc_id
      AND d.source_id <> NEW.source_id
)
BEGIN
    SELECT RAISE(ABORT, 'chunks.source_id must match documents.source_id for doc_id');
END;

CREATE TRIGGER IF NOT EXISTS trg_chunks_source_id_consistency_update
BEFORE UPDATE OF doc_id, source_id ON chunks
FOR EACH ROW
WHEN EXISTS (
    SELECT 1
    FROM documents d
    WHERE d.doc_id = NEW.doc_id
      AND d.source_id <> NEW.source_id
)
BEGIN
    SELECT RAISE(ABORT, 'chunks.source_id must match documents.source_id for doc_id');
END;

CREATE TABLE IF NOT EXISTS research_events (
    event_id TEXT PRIMARY KEY,
    research_domain TEXT NOT NULL,
    event_type TEXT NOT NULL,
    stage TEXT,
    system_context TEXT,
    application_context TEXT,
    outcome TEXT NOT NULL DEFAULT 'unknown',
    failure_reason TEXT NOT NULL DEFAULT 'unknown',
    decision_taken TEXT NOT NULL DEFAULT 'unknown',
    decision_driver TEXT,
    evidence_snippet TEXT NOT NULL,
    evidence_strength TEXT NOT NULL DEFAULT 'unknown',
    confidence TEXT NOT NULL DEFAULT 'low',
    source_id TEXT NOT NULL,
    doc_id TEXT,
    chunk_id TEXT,
    page_number INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE,
    -- Keep events for audit/history when document artifacts are removed; null doc/chunk references are expected.
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE SET NULL,
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    entity_variant TEXT,
    organism TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_entities_type_name ON entities(entity_type, entity_name);
CREATE TABLE IF NOT EXISTS event_entities (
    event_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    role TEXT,
    PRIMARY KEY (event_id, entity_id),
    FOREIGN KEY (event_id) REFERENCES research_events (event_id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities (entity_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (source_entity_id) REFERENCES entities(entity_id) ON DELETE RESTRICT,
    FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS tags (
    tag TEXT PRIMARY KEY
);


CREATE TABLE IF NOT EXISTS event_tags (
    event_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (event_id, tag),
    FOREIGN KEY (event_id) REFERENCES research_events (event_id) ON DELETE CASCADE,
    FOREIGN KEY (tag) REFERENCES tags (tag) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_event_tags_tag ON event_tags(tag);

CREATE TABLE IF NOT EXISTS quantitative_measurements (
    measurement_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    measurement_type TEXT NOT NULL,
    value TEXT NOT NULL,
    unit TEXT NOT NULL,
    context TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (event_id) REFERENCES research_events (event_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_events_domain ON research_events(research_domain);
CREATE INDEX IF NOT EXISTS idx_events_type ON research_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_outcome ON research_events(outcome);
CREATE INDEX IF NOT EXISTS idx_events_failure ON research_events(failure_reason);
CREATE INDEX IF NOT EXISTS idx_events_decision ON research_events(decision_taken);
CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(entity_name);
CREATE INDEX IF NOT EXISTS idx_research_events_source_id ON research_events(source_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON entity_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON entity_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_event_entities_entity_id ON event_entities(entity_id);
CREATE INDEX IF NOT EXISTS idx_event_entities_role ON event_entities(role);
CREATE INDEX IF NOT EXISTS idx_quantitative_measurements_event_id ON quantitative_measurements(event_id);
CREATE INDEX IF NOT EXISTS idx_measurements_type ON quantitative_measurements(measurement_type);
