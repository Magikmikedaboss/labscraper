
from pathlib import Path
import hashlib
from typing import Dict
import sqlite3
import pdfplumber
from datetime import datetime
from utils.common import sha64
from utils.metadata_utils import extract_metadata
from utils.text_utils import chunk_sentences, guess_stage, guess_section
from utils.data_extractors import extract_quantitative_data
from utils.entities import extract_entities
from utils.event_classification import (
    confidence_score,
    ConfidenceInput,
    detect_method_tags,
    detect_failure_reason,
    detect_decision,
    classify_event_type,
    detect_outcome,
    evidence_strength,
)
from utils.db_init import init_db_schema

# Add SEEDS_DIR definition (mirroring run_engine.py)
project_root = Path(__file__).parent.parent.resolve()
SEEDS_DIR = project_root / "input" / "seeds"


# Database functions
def upsert_source(con, source_id: str, pdf_file: str, metadata: Dict):
    """Insert or update source record"""
    now = datetime.now().isoformat()
    con.execute(
        """
        INSERT INTO sources(source_id, pdf_file, title, authors, year, doi, imported_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id) DO UPDATE SET
            pdf_file=excluded.pdf_file,
            title=excluded.title,
            authors=excluded.authors,
            year=excluded.year,
            doi=excluded.doi,
            imported_at=excluded.imported_at
        """,
        (source_id, pdf_file, metadata.get('title'), metadata.get('authors'), 
         metadata.get('year'), metadata.get('doi'), now),
    )

def insert_document(con, source_id: str, file_path: str, sha256: str) -> str:
    """Insert document record"""
    if sha256:
        existing = con.execute(
            "SELECT doc_id FROM documents WHERE sha256 = ? LIMIT 1",
            (sha256,),
        ).fetchone()
        if existing:
            return existing[0]

    doc_id = sha64(f"{source_id}|{file_path}|{sha256}")
    now = datetime.now().isoformat()
    con.execute(
        """INSERT OR IGNORE INTO documents(doc_id, source_id, file_path, file_type, sha256, created_at)
           VALUES (?,?,?,?,?,?)""",
        (doc_id, source_id, file_path, "pdf", sha256, now),
    )
    return doc_id

def insert_chunk(con, source_id: str, doc_id: str, page_number: int, section_guess: str, chunk_text: str) -> str:
    """Insert chunk record"""
    chunk_id = sha64(f"{doc_id}|{page_number}|{chunk_text}")
    now = datetime.now().isoformat()
    con.execute(
        """INSERT OR IGNORE INTO chunks(chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (chunk_id, doc_id, source_id, page_number, section_guess, chunk_text, now),
    )
    return chunk_id

def insert_event(con, source_id: str, doc_id: str, chunk_id: str, page_number: int,
                 domain: str, event_type: str, stage: str, system_context: str | None, application_context: str | None,
                 outcome: str, failure_reason: str, decision_taken: str, decision_driver: str | None,
                 evidence_snippet: str, evidence_strength_v: str, confidence_v: str) -> str:
    """Insert research event record"""
    base = f"{source_id}|{doc_id}|{page_number}|{event_type}|{evidence_snippet[:180]}"
    event_id = sha64(base)
    now = datetime.now().isoformat()
    con.execute(
        """INSERT OR IGNORE INTO research_events(
             event_id, research_domain, event_type, stage, system_context, application_context,
             outcome, failure_reason, decision_taken, decision_driver,
             evidence_snippet, evidence_strength, confidence,
             source_id, doc_id, chunk_id, page_number, created_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event_id, domain, event_type, stage, system_context, application_context,
            outcome, failure_reason, decision_taken, decision_driver,
            evidence_snippet[:500], evidence_strength_v, confidence_v,
            source_id, doc_id, chunk_id, page_number, now
        ),
    )
    return event_id

def link_event_entity(con, event_id: str, entity_id: str, role: str):
    """Link event to entity"""
    con.execute(
        """INSERT OR IGNORE INTO event_entities(event_id, entity_id, role)
           VALUES (?,?,?)""",
        (event_id, entity_id, role),
    )

def link_event_tag(con, event_id: str, tag: str):
    """Link event to tag"""
    con.execute("INSERT OR IGNORE INTO tags(tag) VALUES(?)", (tag,))
    con.execute(
        """INSERT OR IGNORE INTO event_tags(event_id, tag)
           VALUES (?,?)""",
        (event_id, tag),
    )

def insert_measurement(con, event_id: str, measurement: Dict):
    """Insert quantitative measurement"""
    measurement_id = sha64(f"{event_id}|{measurement['measurement_type']}|{measurement['value']}|{measurement['unit']}")
    created_at = datetime.now().isoformat()
    con.execute(
        """INSERT OR IGNORE INTO quantitative_measurements(
            measurement_id, event_id, measurement_type, value, unit, context, created_at
        ) VALUES (?,?,?,?,?,?,?)""",
        (measurement_id, event_id, measurement['measurement_type'], 
         measurement['value'], measurement['unit'], measurement['context'], created_at),
    )

def upsert_entity(con, entity_type: str, entity_name: str, entity_variant: str | None, organism: str | None) -> str:
    """Insert or update entity record"""
    key = f"{entity_type}|{entity_name}|{entity_variant or ''}|{organism or ''}"
    entity_id = sha64(key)
    created_at = datetime.now().isoformat()
    con.execute(
        """INSERT OR IGNORE INTO entities(entity_id, entity_type, entity_name, entity_variant, organism, created_at)
           VALUES (?,?,?,?,?,?)""",
        (entity_id, entity_type, entity_name, entity_variant, organism, created_at),
    )
    return entity_id


def map_research_domain(meta: dict) -> str:
    """Fallback: Guess research domain from metadata dict."""
    for key in ("domain", "research_domain", "field", "area"):
        if key in meta and meta[key]:
            return str(meta[key])
    return "methods_tooling"




def main(input_dir="input/pdfs", db_path="db.sqlite"):
    input_dir = Path(input_dir)
    init_db_schema(db_path)
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        pdfs = list(input_dir.rglob("*.pdf"))
        print(f"Found {len(pdfs)} PDFs in {input_dir} (including subfolders)")
        for pdf_path in pdfs:
            try:
                print(f"\nProcessing: {pdf_path.name}")
                meta = extract_metadata(pdf_path)
                print(f"  Metadata: {meta}")
                # Upsert source and document
                file_bytes = pdf_path.read_bytes()
                source_id = sha64(file_bytes)
                upsert_source(con, source_id, str(pdf_path), meta)
                file_hash = hashlib.sha256(file_bytes).hexdigest()
                doc_id = insert_document(con, source_id, str(pdf_path), file_hash)
                domain = meta.get("domain") or meta.get("research_domain") or map_research_domain(meta) or "methods_tooling"
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, start=1):
                        text = page.extract_text() or ""
                        section = guess_section(text.lower())
                        chunk_id = insert_chunk(con, source_id, doc_id, page_num, section, text)
                        for sent in chunk_sentences(text):
                            ents = extract_entities(sent, domain=domain, SEEDS_DIR=SEEDS_DIR)
                            if not ents:
                                continue
                            measurements = extract_quantitative_data(sent)
                            sent_l = sent.lower()
                            method_tags = detect_method_tags(sent_l)
                            failure_reason = detect_failure_reason(sent_l)
                            decision_taken, decision_driver = detect_decision(sent_l)
                            event_type = classify_event_type(sent_l, method_tags, failure_reason, decision_taken)
                            outcome = detect_outcome(sent_l)
                            evidence_strength_v = evidence_strength(sent_l)
                            stage = guess_stage(sent.lower())
                            confidence = confidence_score(
                                ConfidenceInput(
                                    has_entity=bool(ents),
                                    method_tags=method_tags,
                                    failure_reason=failure_reason,
                                    decision_taken=decision_taken,
                                    has_measurements=bool(measurements),
                                    sentence_l=sent_l
                                )
                            )
                            # Insert event
                            event_id = insert_event(
                                con=con,
                                source_id=source_id,
                                doc_id=doc_id,
                                chunk_id=chunk_id,
                                page_number=page_num,
                                domain=domain,
                                event_type=event_type,
                                stage=stage,
                                system_context=None,
                                application_context=None,
                                outcome=outcome,
                                failure_reason=failure_reason,
                                decision_taken=decision_taken,
                                decision_driver=decision_driver,
                                evidence_snippet=sent,
                                evidence_strength_v=evidence_strength_v,
                                confidence_v=confidence,
                            )
                            # Persist entities and link to event
                            for ent in ents:
                                entity_id = upsert_entity(
                                    con,
                                    ent.get("entity_type", "unknown"),
                                    ent.get("entity_name", "unknown"),
                                    ent.get("entity_variant"),
                                    ent.get("organism")
                                )
                                # Use ent.get("role") if available, else default to "unknown"
                                link_event_entity(con, event_id, entity_id, ent.get("role", "unknown"))
                            # Persist measurements and link to event
                            for measurement in measurements:
                                insert_measurement(con, event_id, measurement)
                            print(f"    Inserted event: {event_id} (page {page_num})")
            except Exception as e:
                print(f"❌ Error processing {pdf_path}: {e}")
                # Optionally record failure status in DB for this source
                try:
                    try:
                        fail_source_id = sha64(pdf_path.read_bytes()) if pdf_path.exists() else sha64(str(pdf_path))
                    except Exception:
                        fail_source_id = sha64(str(pdf_path))
                    upsert_source(
                        con,
                        fail_source_id,
                        str(pdf_path),
                        {
                            "title": f"[FAILED] {str(e)[:200]}",
                            "authors": "",
                            "year": None,
                            "doi": None,
                        }
                    )
                except Exception as db_e:
                    print(f"   (DB error while recording failure for {pdf_path}: {db_e})")
                continue


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Modular PDF-to-DB pipeline")
    parser.add_argument('--input-dir', type=str, default="input/pdfs", help="Input directory containing PDFs")
    parser.add_argument('--db-path', type=str, default="db.sqlite", help="Path to output SQLite database")
    args = parser.parse_args()
    main(input_dir=args.input_dir, db_path=args.db_path)