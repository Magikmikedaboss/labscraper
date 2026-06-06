PRAGMA foreign_keys = ON;

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
