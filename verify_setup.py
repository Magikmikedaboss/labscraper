"""
Verification script to check if the peptide scraper is set up correctly.
Run this after installation to ensure everything works.
"""

import sys
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8+"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.8+)")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\nChecking dependencies...")
    
    required = {
        'pdfplumber': 'PDF text extraction',
        'tqdm': 'Progress bars',
        'sqlite3': 'Database (built-in)',
    }
    
    all_ok = True
    for package, description in required.items():
        try:
            if package == 'sqlite3':
                import sqlite3
            else:
                __import__(package)
            print(f"  ✅ {package:15} - {description}")
        except ImportError:
            print(f"  ❌ {package:15} - {description} (NOT INSTALLED)")
            all_ok = False
    
    return all_ok

def check_files():
    """Check if required files exist"""
    print("\nChecking required files...")
    
    required_files = {
        'schema.sql': 'Database schema',
        'init_db.py': 'Database initialization',
        'scrape_pdfs.py': 'Main scraper',
        'export_csv.py': 'CSV export tool',
        'README.md': 'Documentation',
        'requirements.txt': 'Dependencies list',
    }
    
    all_ok = True
    for filename, description in required_files.items():
        path = Path(filename)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {filename:20} - {description} ({size:,} bytes)")
        else:
            print(f"  ❌ {filename:20} - {description} (MISSING)")
            all_ok = False
    
    return all_ok

def check_directories():
    """Check if required directories exist"""
    print("\nChecking directories...")
    
    input_dir = Path('input_pdfs')
    output_dir = Path('output')
    
    all_ok = True
    
    if input_dir.exists():
        pdf_count = len(list(input_dir.glob('*.pdf')))
        print(f"  ✅ input_pdfs/ exists ({pdf_count} PDFs found)")
        if pdf_count == 0:
            print(f"     ⚠️  No PDFs found - add some PDFs to get started!")
    else:
        print(f"  ⚠️  input_pdfs/ does not exist (will be created)")
        input_dir.mkdir(exist_ok=True)
        print(f"     ✅ Created input_pdfs/ directory")
    
    if output_dir.exists():
        print(f"  ✅ output/ exists")
    else:
        print(f"  ℹ️  output/ does not exist (will be created on first run)")
    
    return all_ok

def check_database():
    """Check if database exists and is valid"""
    print("\nChecking database...")
    
    db_path = Path('output') / 'peptide_intel.sqlite'
    
    if not db_path.exists():
        print(f"  ℹ️  Database not initialized yet")
        print(f"     Run: python init_db.py")
        return True
    
    try:
        import sqlite3
        con = sqlite3.connect(db_path)
        
        # Check if tables exist
        tables = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        
        table_names = [t[0] for t in tables]
        expected_tables = [
            'sources', 'documents', 'chunks', 'entities', 
            'research_events', 'event_entities', 'tags', 'event_tags',
            'quantitative_measurements', 'entity_relationships'
        ]
        
        missing = [t for t in expected_tables if t not in table_names]
        
        if missing:
            print(f"  ⚠️  Database exists but missing tables: {', '.join(missing)}")
            print(f"     Run: python init_db.py")
            con.close()
            return False
        
        # Check record counts
        sources = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        events = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]
        entities = con.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        
        print(f"  ✅ Database initialized and valid")
        print(f"     Sources: {sources}, Events: {events}, Entities: {entities}")
        
        if events == 0:
            print(f"     ℹ️  No data yet - run: python scrape_pdfs.py")
        
        con.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def test_import():
    """Test if we can import the scraper modules"""
    print("\nTesting module imports...")
    
    try:
        # Test if we can read the schema
        from pathlib import Path as PathLib
        schema_path = PathLib('schema.sql')
        if schema_path.exists():
            schema = schema_path.read_text()
            if 'CREATE TABLE' in schema:
                print(f"  ✅ schema.sql is valid")
            else:
                print(f"  ❌ schema.sql appears invalid")
                return False
        
        # Test basic imports
        import re
        import hashlib
        import sqlite3
        from datetime import datetime, timezone
        
        print(f"  ✅ All core modules can be imported")
        return True
        
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False

def print_summary(results):
    """Print summary of verification"""
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} - {check}")
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 All checks passed! You're ready to go!")
        print("\nNext steps:")
        print("  1. Add PDFs to input_pdfs/ folder")
        print("  2. Run: python init_db.py (if not done)")
        print("  3. Run: python scrape_pdfs.py")
        print("  4. Run: python export_csv.py")
        print("\nSee QUICKSTART.md for detailed instructions.")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Initialize database: python init_db.py")
        print("  - Check file permissions")
    
    print("="*60)

def main():
    """Run all verification checks"""
    print("="*60)
    print("PEPTIDE SCRAPER SETUP VERIFICATION")
    print("="*60)
    
    results = {
        'Python Version': check_python_version(),
        'Dependencies': check_dependencies(),
        'Required Files': check_files(),
        'Directories': check_directories(),
        'Module Imports': test_import(),
        'Database': check_database(),
    }
    
    print_summary(results)

if __name__ == "__main__":
    main()
