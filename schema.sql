PRAGMA foreign_keys = ON;

-- =========================================================
-- 1) SOURCES (the paper / report itself)
-- =========================================================
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,            -- DOI if you have it; otherwise hash of pdf filename
  title TEXT,
  authors TEXT,
  year INTEGER,
  publication_date TEXT,                 -- YYYY-MM-DD when available
  venue TEXT,                            -- journal / preprint / conference
  doi TEXT,
  url TEXT,
  domain TEXT,
  pdf_file TEXT,                         -- local file name
  imported_at TEXT,
  last_seen_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sources_year ON sources(year);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_sources_doi
ON sources(doi)
WHERE doi IS NOT NULL AND trim(doi) <> '';


-- =========================================================
-- 2) DOCUMENTS (a local artifact you processed)
-- =========================================================
CREATE TABLE IF NOT EXISTS documents (
  doc_id TEXT PRIMARY KEY,               -- hash/uuid
  source_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_type TEXT NOT NULL DEFAULT 'pdf', -- pdf/html/xml
  sha256 TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source_id);
CREATE UNIQUE INDEX IF NOT EXISTS uniq_documents_sha256
ON documents(sha256)
WHERE sha256 IS NOT NULL AND trim(sha256) <> '';


CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY,             -- hash/uuid
  doc_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  page_number INTEGER,                   -- nullable for HTML
  section_guess TEXT,                    -- Methods / Results / Discussion / etc (optional)
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

CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);



-- =========================================================
-- 4) ENTITIES (what the sentence is about)
--    This is how you become multi-domain.
-- =========================================================
CREATE TABLE IF NOT EXISTS entities (
  entity_id TEXT PRIMARY KEY,            -- stable id (hash of name+type), or uuid
  entity_type TEXT NOT NULL,             -- peptide | stem_cell | compound | gene | scaffold | device | protocol | biomarker | etc
  entity_name TEXT NOT NULL,             -- sequence, "MSC", "iPSC", "rapamycin", "AAV9", etc
  entity_variant TEXT,                   -- modified/differentiated/donor-type/formulation/etc
  organism TEXT,                         -- human/mouse/rat/etc (optional)
  created_at TEXT DEFAULT (datetime('now'))
);

-- Ensure no duplicate (entity_type, entity_name) pairs
CREATE UNIQUE INDEX IF NOT EXISTS uniq_entities_type_name ON entities(entity_type, entity_name);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(entity_name);


-- =========================================================
-- 5) EVENTS (the money table)
--    Each row = one "research-relevant event" with evidence.
-- =========================================================
CREATE TABLE IF NOT EXISTS research_events (
  event_id TEXT PRIMARY KEY,             -- hash/uuid

  -- What domain/run this came from
  research_domain TEXT NOT NULL,         -- peptide | stem_cell | anti_aging | oncology | materials | etc

  -- What kind of event this is
  event_type TEXT NOT NULL,              -- method_evaluation | stability_issue | efficacy_result | toxicity_flag |
                                         -- manufacturing_constraint | regulatory_risk | assay_limitation |
                                         -- cost_tradeoff | reproducibility_issue | decision_point | other

  -- Context (high value for filtering)
  stage TEXT,                            -- in_silico | in_vitro | ex_vivo | in_vivo | clinical | unknown
  system_context TEXT,                   -- "human fibroblasts", "mouse model", "serum", "organoid", etc
  application_context TEXT,              -- anti-aging, wound healing, regenerative, etc

  -- Outcome + decision intelligence
  outcome TEXT NOT NULL DEFAULT 'unknown',           -- failed | weak | moderate | improved | successful | unknown
  failure_reason TEXT NOT NULL DEFAULT 'unknown',    -- stability_failure | no_activity | toxicity_flag | scalability |
                                                     -- regulatory | cost | reproducibility | unknown
  decision_taken TEXT NOT NULL DEFAULT 'unknown',    -- continued | modified | abandoned | paused | replicated | escalated | unknown
  decision_driver TEXT,                              -- stability | cost | safety | scalability | regulatory | reproducibility | unknown

  -- Evidence and trust
  evidence_snippet TEXT NOT NULL,         -- short sentence/paragraph excerpt
  evidence_strength TEXT NOT NULL DEFAULT 'unknown', -- weak | moderate | strong | unknown
  confidence TEXT NOT NULL DEFAULT 'low', -- low | med | high

  -- Traceability
  source_id TEXT NOT NULL,
  doc_id TEXT,
  chunk_id TEXT,
  page_number INTEGER,

  -- housekeeping
  created_at TEXT DEFAULT (datetime('now')),

  FOREIGN KEY (source_id) REFERENCES sources(source_id) ON DELETE CASCADE,
  -- Keep events for audit/history when document artifacts are removed; null doc/chunk references are expected.
  FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE SET NULL,
  FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_events_domain ON research_events(research_domain);
CREATE INDEX IF NOT EXISTS idx_events_type ON research_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_outcome ON research_events(outcome);
CREATE INDEX IF NOT EXISTS idx_events_failure ON research_events(failure_reason);
CREATE INDEX IF NOT EXISTS idx_events_decision ON research_events(decision_taken);
CREATE INDEX IF NOT EXISTS idx_events_source ON research_events(source_id);


-- =========================================================
-- 6) EVENT ↔ ENTITY LINKS (many-to-many)
--    One event can mention multiple entities.
-- =========================================================
CREATE TABLE IF NOT EXISTS event_entities (
  event_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  role TEXT,                             -- tested | comparator | target | biomarker | method_component | unknown
  PRIMARY KEY (event_id, entity_id),
  FOREIGN KEY (event_id) REFERENCES research_events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_event_entities_role ON event_entities(role);


-- =========================================================
-- 7) TAGS (flexible labels without schema changes)
-- =========================================================
CREATE TABLE IF NOT EXISTS tags (
  tag TEXT PRIMARY KEY                   -- "lc-ms/ms", "fluorescent", "nitrosamine", "GMP", etc
);

CREATE TABLE IF NOT EXISTS event_tags (
  event_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  PRIMARY KEY (event_id, tag),
  FOREIGN KEY (event_id) REFERENCES research_events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (tag) REFERENCES tags(tag) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_event_tags_tag ON event_tags(tag);


-- =========================================================
-- 8) QUANTITATIVE MEASUREMENTS (numerical data extraction)
-- =========================================================

-- NOTE: value column changed from REAL to TEXT for high-precision decimal storage.
-- For existing databases, run the migration inside a transaction:
--   BEGIN TRANSACTION;
--   ALTER TABLE quantitative_measurements RENAME TO quantitative_measurements_old;
--   CREATE TABLE quantitative_measurements (... value TEXT ...);
--   INSERT INTO quantitative_measurements SELECT ... CAST(value AS TEXT) ... FROM quantitative_measurements_old;
--   Verify row counts, NULL constraints, and foreign key integrity match.
--   If verification fails, ROLLBACK so quantitative_measurements_old is preserved.
--   DROP TABLE quantitative_measurements_old;
--   COMMIT;
CREATE TABLE IF NOT EXISTS quantitative_measurements (
  measurement_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  measurement_type TEXT NOT NULL,       -- ic50 | ec50 | half_life | stability_percent | kd | ki | etc
  value TEXT NOT NULL,
  unit TEXT NOT NULL,                   -- nM | μM | mM | min | hour | day | percent | etc
  context TEXT,                         -- the phrase where this was found
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (event_id) REFERENCES research_events(event_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_measurements_type ON quantitative_measurements(measurement_type);
CREATE INDEX IF NOT EXISTS idx_measurements_event ON quantitative_measurements(event_id);


-- =========================================================
-- 9) ENTITY RELATIONSHIPS (comparative statements)
-- =========================================================
CREATE TABLE IF NOT EXISTS entity_relationships (
  relationship_id TEXT PRIMARY KEY,
  source_entity_id TEXT NOT NULL,       -- subject entity
  target_entity_id TEXT NOT NULL,       -- object entity
  relationship_type TEXT NOT NULL,      -- more_stable_than | more_potent_than | analog_of | 
                                        -- derivative_of | less_toxic_than | etc
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (source_entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE,
  FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_relationships_type ON entity_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON entity_relationships(target_entity_id);
