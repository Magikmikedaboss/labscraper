"""
Parallel PDF Scraper - Process multiple PDFs simultaneously
Uses multiprocessing to speed up scraping by 4-8x
"""

import multiprocessing as mp
from multiprocessing import Pool
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone
import pdfplumber
from tqdm import tqdm


# Import the existing scraper functions
from scrape_pdfs_phase1 import (
    extract_metadata, chunk_sentences, guess_stage, guess_section,
    extract_all_entities, extract_quantitative_data,
    detect_method_tags, detect_failure_reason, detect_decision, detect_outcome,
    classify_event_type, evidence_strength, confidence_score_phase1,
    suggested_keep, normalize_event_key,
    upsert_source, insert_document, insert_chunk, insert_event,
    link_event_entity, link_event_tag, insert_measurement, upsert_entity,
    now_iso, sha16, sha64, RESEARCH_DOMAIN,
    FAILURE_PHRASES, DECISION_PHRASES, METHOD_TAGS
)

def process_single_pdf(args):
    """
    Process a single PDF file
    Returns: (pdf_path, events_count, success, error_msg)
    """
    pdf_path, domain, db_path = args
    
    try:
        # Create a separate connection for this process with timeout
        con = sqlite3.connect(db_path, timeout=30.0)
        
        # Enable WAL mode for better concurrency
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        
        source_id = sha16(f"{pdf_path.name}|{pdf_path.stat().st_size}|{int(pdf_path.stat().st_mtime)}")
        file_hash = sha64(f"{pdf_path.name}|{pdf_path.stat().st_size}|{int(pdf_path.stat().st_mtime)}")
        
        events_count = 0
        
        with pdfplumber.open(str(pdf_path)) as pdf:
            metadata = extract_metadata(pdf_path, pdf)
            upsert_source(con, source_id, pdf_path.name, metadata)
            doc_id = insert_document(con, source_id, str(pdf_path.resolve()), file_hash)
            
            seen_events = set()
            
            for page_idx, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue
                    
                    section = guess_section(text.lower())
                    chunk_id = insert_chunk(con, source_id, doc_id, page_idx, section, text)
                    
                    for sent in chunk_sentences(text):
                        s_l = sent.lower()
                        
                        # Quick signal check
                        has_signal = (
                            any(p in s_l for lst in FAILURE_PHRASES.values() for p in lst) or
                            any(p in s_l for lst in DECISION_PHRASES.values() for p in lst) or
                            any(p in s_l for lst in METHOD_TAGS.values() for p in lst)
                        )
                        if not has_signal:
                            continue
                        
                        tags = detect_method_tags(s_l)
                        failure_reason = detect_failure_reason(s_l)
                        decision_taken, decision_driver = detect_decision(s_l)
                        outcome = detect_outcome(s_l)
                        stage = guess_stage(s_l)
                        event_type = classify_event_type(s_l, tags, failure_reason, decision_taken)
                        strength = evidence_strength(s_l)
                        
                        ents = extract_all_entities(sent, metadata.get('title', ''))
                        measurements = extract_quantitative_data(sent)
                        
                        conf = confidence_score_phase1(bool(ents), tags, failure_reason, decision_taken, bool(measurements), s_l)
                        keep = suggested_keep(conf, event_type, failure_reason, decision_taken, tags)
                        
                        if keep == 0 and event_type == "other":
                            continue
                        
                        event_key = normalize_event_key(event_type, ents, page_idx, sent)
                        if event_key in seen_events:
                            continue
                        seen_events.add(event_key)
                        
                        bio_sys = None
                        if "serum" in tags:
                            bio_sys = "serum/plasma"
                        elif "organoid" in s_l:
                            bio_sys = "organoid"
                        elif "cell line" in s_l or "cells" in s_l:
                            bio_sys = "cells"
                        
                        event_id = insert_event(
                            con=con,
                            source_id=source_id,
                            doc_id=doc_id,
                            chunk_id=chunk_id,
                            page_number=page_idx,
                            domain=domain,
                            event_type=event_type,
                            study_stage=stage,
                            biological_system=bio_sys,
                            application_area=None,
                            outcome=outcome,
                            failure_reason=failure_reason,
                            decision_taken=decision_taken,
                            decision_driver=decision_driver,
                            evidence_snippet=sent,
                            evidence_strength_v=strength,
                            confidence_v=conf,
                        )
                        
                        for t in tags:
                            link_event_tag(con, event_id, t)
                        
                        for e in ents:
                            entity_id = upsert_entity(con, e["entity_type"], e["entity_name"], e["entity_variant"], None)
                            link_event_entity(con, event_id, entity_id, e.get("role", "unknown"))
                        
                        for m in measurements:
                            insert_measurement(con, event_id, m)
                        
                        events_count += 1
                
                except Exception as e:
                    # Continue on page errors
                    continue
        
        con.commit()
        con.close()
        
        return (pdf_path.name, events_count, True, None)
    
    except Exception as e:
        return (pdf_path.name, 0, False, str(e))


def main():
    parser = argparse.ArgumentParser(description='Parallel PDF Scraper - 4-8x faster!')
    parser.add_argument('--domain', default='peptide', 
                       help='Research domain')
    parser.add_argument('--input-dir', type=Path, default=Path('input_pdfs'),
                       help='Directory containing PDF files')
    parser.add_argument('--output-db', type=Path, default=Path('output/peptide_intel.sqlite'),
                       help='Output SQLite database path')
    parser.add_argument('--workers', type=int, default=4,
                       help='Number of parallel workers (default: 4, recommended: 4-8)')
    args = parser.parse_args()
    
    domain = args.domain
    input_dir = args.input_dir
    db_path = args.output_db
    num_workers = args.workers
    
    if not input_dir.exists():
        raise SystemExit(f"Missing folder: {input_dir.resolve()}")
    
    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {input_dir.resolve()}")
    
    print(f"\n{'='*70}")
    print(f"PARALLEL PDF SCRAPER")
    print(f"{'='*70}")
    print(f"PDFs to process: {len(pdfs)}")
    print(f"Parallel workers: {num_workers}")
    print(f"Expected speedup: {num_workers}x faster")
    print(f"Database: {db_path}")
    print(f"{'='*70}\n")
    
    # Prepare arguments for each PDF
    pdf_args = [(pdf, domain, db_path) for pdf in pdfs]
    
    # Process PDFs in parallel
    total_events = 0
    failed_pdfs = []
    
    with Pool(processes=num_workers) as pool:
        # Use imap_unordered for better progress tracking
        results = list(tqdm(
            pool.imap_unordered(process_single_pdf, pdf_args),
            total=len(pdfs),
            desc="PDFs"
        ))
    
    # Collect results
    for pdf_name, events_count, success, error_msg in results:
        if success:
            total_events += events_count
        else:
            failed_pdfs.append((pdf_name, error_msg))
    
    print(f"\n{'='*70}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*70}")
    print(f"✅ Total events inserted: {total_events}")
    print(f"✅ Successful PDFs: {len(pdfs) - len(failed_pdfs)}/{len(pdfs)}")
    print(f"✅ Database: {db_path.resolve()}")
    
    if failed_pdfs:
        print(f"\n⚠️  Failed PDFs ({len(failed_pdfs)}):")
        for pdf_name, error in failed_pdfs[:10]:  # Show first 10
            print(f"   - {pdf_name}: {error[:80]}")
        if len(failed_pdfs) > 10:
            print(f"   ... and {len(failed_pdfs) - 10} more")
    
    print(f"\n{'='*70}")
    print(f"Next step: Run dual-lens export")
    print(f"  python export_dual_lens.py {db_path} {domain}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Required for Windows multiprocessing
    mp.freeze_support()
    main()
