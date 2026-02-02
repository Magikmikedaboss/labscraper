#!/usr/bin/env python3
"""
Test script to verify end-to-end construction science scraping works correctly.
This creates a clean test database and scrapes a few construction PDFs to verify
the domain fix works in practice.
"""

import sys
import sqlite3
from pathlib import Path
import tempfile
import shutil

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))

def test_construction_scrape():
    """Test end-to-end construction science scraping"""
    print("🏗️  Testing End-to-End Construction Science Scraping")
    print("=" * 60)
    
    # Check if input_pdfs directory exists and has PDFs
    input_dir = Path("input_pdfs")
    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        print("Please create an 'input_pdfs' directory with some construction PDFs to test with.")
        return False
    
    pdfs = list(input_dir.glob("*.pdf"))
    if not pdfs:
        print(f"❌ No PDFs found in {input_dir}")
        print("Please add some construction PDFs to test with.")
        return False
    
    print(f"📁 Found {len(pdfs)} PDFs in {input_dir}")
    print("Sample PDFs:")
    for pdf in pdfs[:3]:
        print(f"  - {pdf.name}")
    if len(pdfs) > 3:
        print(f"  ... and {len(pdfs) - 3} more")
    print()
    
    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp_db:
        db_path = Path(tmp_db.name)
    
    try:
        print(f"🔧 Testing with temporary database: {db_path.name}")
        print(f"🚀 Running construction science scrape...")
        print()
        
        # Import and run the parallel scraper
        from scrape_pdfs_parallel import main as scrape_main
        from argparse import Namespace
        
        # Create args for construction science domain
        args = Namespace(
            domain="construction_science",
            input_dir=input_dir,
            output_db=db_path,
            workers=2  # Use fewer workers for testing
        )
        
        # Run the scraper (this will test our domain fix)
        print("Processing PDFs with construction_science domain...")
        print("This will verify that only construction entities are extracted.")
        print()
        
        # We'll simulate the main function call
        from scrape_pdfs_parallel import _ensure_db_schema, process_single_pdf
        from scrape_pdfs_parallel import _db_has_all_tables
        import multiprocessing as mp
        from multiprocessing import Pool
        from tqdm import tqdm
        
        # Ensure schema is initialized
        _ensure_db_schema(db_path)
        
        # Prepare jobs for first 2 PDFs only (to keep test fast)
        test_pdfs = pdfs[:2]
        jobs = [(str(p), "construction_science", str(db_path)) for p in test_pdfs]
        
        print(f"Processing {len(test_pdfs)} PDFs...")
        total_events = 0
        failed = []
        
        with Pool(processes=2) as pool:
            for pdf_name, events_count, ok, err in tqdm(
                pool.imap_unordered(process_single_pdf, jobs),
                total=len(jobs),
                desc="PDFs"
            ):
                if ok:
                    total_events += events_count
                    print(f"  ✅ {pdf_name}: {events_count} events")
                else:
                    failed.append((pdf_name, err))
                    print(f"  ❌ {pdf_name}: {err}")
        
        print()
        print("📊 SCRAPING RESULTS:")
        print(f"   Total events extracted: {total_events}")
        print(f"   Successful PDFs: {len(test_pdfs) - len(failed)}/{len(test_pdfs)}")
        print(f"   Database: {db_path.resolve()}")
        print()
        
        if failed:
            print(f"⚠️  Failed PDFs ({len(failed)}):")
            for pdf_name, err in failed:
                print(f"   - {pdf_name}: {err[:100]}")
            print()
        
        # Analyze the extracted entities
        print("🔍 ANALYZING EXTRACTED ENTITIES:")
        print("Checking if entities are construction-specific...")
        print()
        
        with sqlite3.connect(db_path) as con:
            # Get entity types and counts
            entity_stats = con.execute("""
                SELECT e.entity_type, COUNT(*) as count, GROUP_CONCAT(DISTINCT e.entity_name, ', ') as examples
                FROM entities e
                JOIN event_entities ee ON e.entity_id = ee.entity_id
                JOIN research_events re ON ee.event_id = re.event_id
                WHERE re.research_domain = 'construction_science'
                GROUP BY e.entity_type
                ORDER BY count DESC
            """).fetchall()
            
            if entity_stats:
                print("Entity types extracted:")
                for entity_type, count, examples in entity_stats:
                    print(f"  {entity_type}: {count} entities")
                    print(f"    Examples: {examples[:100]}...")
                print()
                
                # Check for domain contamination
                construction_entity_types = {'material', 'system', 'environment', 'failure_mode', 'hazard', 'test_method'}
                biomedical_entity_types = {'peptide', 'compound', 'target', 'model', 'stem_cell', 'neural_cell'}
                
                extracted_types = {row[0] for row in entity_stats}
                construction_types = extracted_types & construction_entity_types
                biomedical_types = extracted_types & biomedical_entity_types
                
                print("✅ Domain Analysis:")
                print(f"   Construction entity types found: {len(construction_types)}")
                print(f"   Biomedical entity types found: {len(biomedical_types)}")
                
                if biomedical_types:
                    print(f"   ❌ DOMAIN CONTAMINATION: Found biomedical entities: {biomedical_types}")
                    print("   This suggests the domain fix may not be working properly.")
                else:
                    print(f"   ✅ CLEAN: Only construction entities found, no biomedical contamination!")
                
                if construction_types:
                    print(f"   ✅ CONSTRUCTION ENTITIES: {construction_types}")
                else:
                    print(f"   ⚠️  WARNING: No construction entities found - check your PDFs")
                
            else:
                print("❌ No entities found in database - check if PDFs contain construction content")
        
        return len(biomedical_types) == 0 and len(construction_types) > 0
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up temporary database
        if db_path.exists():
            db_path.unlink()

def main():
    """Run the construction scrape test"""
    print("🧪 CONSTRUCTION SCIENCE END-TO-END TEST")
    print("=" * 60)
    print()
    print("This test will:")
    print("1. Create a temporary database")
    print("2. Scrape construction PDFs with construction_science domain")
    print("3. Verify only construction entities are extracted")
    print("4. Check for domain contamination")
    print()
    
    success = test_construction_scrape()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 CONSTRUCTION SCIENCE DOMAIN FIX VERIFIED!")
        print("✅ The domain leakage issue has been resolved.")
        print("✅ Construction PDFs now extract only construction entities.")
        print("✅ Ready for production use with construction_science domain.")
    else:
        print("❌ CONSTRUCTION SCIENCE DOMAIN FIX NEEDS MORE WORK")
        print("❌ Domain contamination or extraction issues detected.")
        print("❌ Check the error messages above for details.")
    print("=" * 60)

if __name__ == "__main__":
    main()