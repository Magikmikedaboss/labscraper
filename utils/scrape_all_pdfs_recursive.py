"""
Recursive PDF Scraper - Scans all PDFs in all folders and subfolders
Combines everything into one database for comprehensive analysis
"""

import argparse
from pathlib import Path
import sqlite3
from utils.scrape_pdfs_parallel import process_single_pdf
from multiprocessing import Pool
from tqdm import tqdm
import multiprocessing as mp


def find_all_pdfs(root_dirs):
    """
    Recursively find all PDF files in given directories
    
    Args:
        root_dirs: List of root directories to search
    
    Returns:
        List of Path objects for all PDFs found
    """
    all_pdfs = []
    
    for root_dir in root_dirs:
        root_path = Path(root_dir)
        
        if not root_path.exists():
            print(f"⚠️  Directory not found: {root_path}")
            continue
        
        # Recursively find all PDFs (case-insensitive)
        pdfs = [p for p in root_path.rglob("*") if p.suffix.lower() == ".pdf"]
        all_pdfs.extend(pdfs)
        
        print(f"📁 {root_path.name}: Found {len(pdfs)} PDFs")
    
    return all_pdfs


def main():
    parser = argparse.ArgumentParser(
        description='Recursive PDF Scraper - Scan ALL PDFs in folders and subfolders'
    )
    parser.add_argument(
        '--root-dirs',
        nargs='+',
        required=True,
        help='Root directories to scan (can specify multiple)'
    )
    parser.add_argument(
        '--domain',
        default='biohacking_longevity',
        help='Research domain (default: biohacking_longevity)'
    )
    parser.add_argument(
        '--output-db',
        type=Path,
        default=Path('output/all_pdfs_combined.sqlite'),
        help='Output SQLite database path'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4, max recommended: 8)'
    )
    
    args = parser.parse_args()
    
    root_dirs = [Path(d) for d in args.root_dirs]
    domain = args.domain
    db_path = args.output_db
    num_workers = args.workers
    
    print("\n" + "="*70)
    print("RECURSIVE PDF SCRAPER - SCAN ALL FOLDERS")
    print("="*70)
    print(f"Root directories: {len(root_dirs)}")
    for root_dir in root_dirs:
        print(f"  - {root_dir}")
    print(f"Domain: {domain}")
    print(f"Workers: {num_workers}")
    print(f"Output DB: {db_path}")
    print("="*70 + "\n")
    
    # Find all PDFs recursively
    print("🔍 Scanning for PDFs...")
    all_pdfs = find_all_pdfs(root_dirs)
    
    if not all_pdfs:
        print("❌ No PDFs found!")
        return
    
    print(f"\n✅ Total PDFs found: {len(all_pdfs)}")
    print("📊 Estimated time:")
    print(f"   Sequential: ~{len(all_pdfs) * 15 / 60:.1f} minutes")
    print(f"   Parallel ({num_workers} workers): ~{len(all_pdfs) * 15 / 60 / num_workers:.1f} minutes")
    print()
    
    # Show folder breakdown
    folder_counts = {}
    for pdf in all_pdfs:
        folder = pdf.parent
        folder_counts[folder] = folder_counts.get(folder, 0) + 1
    
    print(f"📂 Folder breakdown ({len(folder_counts)} folders):")
    for folder, count in sorted(folder_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {folder.name}: {count} PDFs")
    if len(folder_counts) > 10:
        print(f"   ... and {len(folder_counts) - 10} more folders")
    print()
    
    # Confirm before proceeding
    response = input(f"🚀 Ready to scrape {len(all_pdfs)} PDFs? (y/n): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return
    
    # Initialize database if it doesn't exist or is empty
    print(f"\n{'='*70}")
    print("INITIALIZING DATABASE")
    print(f"{'='*70}\n")
    
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if database needs initialization
    needs_init = True
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as con:
                # Check if tables exist
                tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if len(tables) > 0:
                    needs_init = False
                    print(f"✅ Database already initialized with {len(tables)} tables")
        except Exception as e:
            print(f"⚠️  Database check failed: {e}")
            needs_init = True
    
    if needs_init:
        print("🔧 Initializing database schema...")
        script_dir = Path(__file__).resolve().parent
        schema_path = script_dir / "schema.sql"
        if not schema_path.exists():
            print(f"❌ Schema file not found: {schema_path}")
            return
        
        schema = schema_path.read_text(encoding="utf-8")
        con = sqlite3.connect(db_path)
        try:
            con.executescript(schema)
            con.commit()
            print("✅ Database initialized successfully")
        finally:
            con.close()
    
    print(f"\n{'='*70}")
    print("STARTING PARALLEL SCRAPE")
    print(f"{'='*70}\n")
    
    # Prepare arguments for parallel processing
    pdf_args = [(pdf, domain, db_path) for pdf in all_pdfs]
    
    # Process PDFs in parallel
    total_events = 0
    failed_pdfs = []
    
    with Pool(processes=num_workers) as pool:
        results = list(tqdm(
            pool.imap_unordered(process_single_pdf, pdf_args),
            total=len(all_pdfs),
            desc="PDFs"
        ))
    
    # Collect results
    for pdf_name, events_count, success, error_msg in results:
        if success:
            total_events += events_count
        else:
            failed_pdfs.append((pdf_name, error_msg))
    
    print(f"\n{'='*70}")
    print("SCRAPING COMPLETE")
    print(f"{'='*70}")
    print(f"✅ Total PDFs processed: {len(all_pdfs)}")
    print(f"✅ Successful: {len(all_pdfs) - len(failed_pdfs)}")
    print(f"✅ Total events extracted: {total_events}")
    print(f"✅ Database: {db_path.resolve()}")
    
    if failed_pdfs:
        print(f"\n⚠️  Failed PDFs ({len(failed_pdfs)}):")
        for pdf_name, error in failed_pdfs[:10]:
            print(f"   - {pdf_name}: {(error or 'Unknown error')[:80]}")
        if len(failed_pdfs) > 10:
            print(f"   ... and {len(failed_pdfs) - 10} more")    
    # Show database stats
    print(f"\n{'='*70}")
    print("DATABASE STATISTICS")
    print(f"{'='*70}")
    
    with sqlite3.connect(db_path) as con:
        # Count events
        event_count = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]
        print(f"📊 Total events in database: {event_count}")
        
        # Count entities
        entity_count = con.execute("SELECT COUNT(DISTINCT entity_id) FROM entities").fetchone()[0]
        print(f"🏷️  Total unique entities: {entity_count}")
        
        # Count papers
        paper_count = con.execute("SELECT COUNT(DISTINCT source_id) FROM sources").fetchone()[0]
        print(f"📄 Total papers: {paper_count}")    
    print(f"\n{'='*70}")
    print("NEXT STEP: Run dual-lens export")
    print(f"  python export_dual_lens.py {db_path} {domain}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    mp.freeze_support()
    main()
