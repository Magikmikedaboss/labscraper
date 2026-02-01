PRAGMA foreign_keys = ON;

-- Schema for peptide_intel_construction.sqlite (Phase 1, multi-domain, multi-lens)

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    pdf_file TEXT,
    title TEXT,
    authors TEXT,
    year INTEGER,
    doi TEXT,
    venue TEXT,
    imported_at TEXT
);
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    source_id TEXT,
    file_path TEXT,
    file_type TEXT,
    sha256 TEXT,
    created_at TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
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
    source_id TEXT,
    doc_id TEXT,
    chunk_id TEXT,
    page_number INTEGER,
    created_at TEXT,
    FOREIGN KEY (source_id) REFERENCES sources(source_id),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id)
);

CREATE TABLE IF NOT EXISTS event_entities (
    event_id TEXT,
    entity_id TEXT,
    role TEXT,
    PRIMARY KEY (event_id, entity_id, role),
    FOREIGN KEY (event_id) REFERENCES research_events(event_id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE TABLE IF NOT EXISTS tags (
    tag TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS event_tags (
    event_id TEXT,
    tag TEXT,
    PRIMARY KEY (event_id, tag),
    FOREIGN KEY (event_id) REFERENCES research_events(event_id),
    FOREIGN KEY (tag) REFERENCES tags(tag)
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

CREATE TABLE IF NOT EXISTS quantitative_measurements (
    measurement_id TEXT PRIMARY KEY,
    event_id TEXT,
    measurement_type TEXT,
    value REAL,
    unit TEXT,
    context TEXT,
    created_at TEXT,
    FOREIGN KEY (event_id) REFERENCES research_events(event_id)
);