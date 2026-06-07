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

CREATE TRIGGER IF NOT EXISTS trg_documents_source_id_consistency_insert
BEFORE INSERT ON documents
FOR EACH ROW
WHEN EXISTS (
    SELECT 1
    FROM chunks c
    WHERE c.doc_id = NEW.doc_id
      AND c.source_id <> NEW.source_id
)
BEGIN
    SELECT RAISE(ABORT, 'documents.source_id insert would violate chunks.source_id consistency for doc_id');
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_source_id_consistency_update
BEFORE UPDATE OF source_id ON documents
FOR EACH ROW
WHEN EXISTS (
    SELECT 1
    FROM chunks c
    WHERE c.doc_id = NEW.doc_id
      AND c.source_id <> NEW.source_id
)
BEGIN
    SELECT RAISE(ABORT, 'documents.source_id update would violate chunks.source_id consistency for doc_id');
END;
