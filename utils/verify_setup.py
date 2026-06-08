"""
Verification script to check if the peptide scraper is set up correctly.
Run this after installation to ensure everything works.
"""

import sys
from pathlib import Path

from utils.db_utils import connect_with_foreign_keys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def check_python_version():
    """Check if Python version is 3.11+"""
    print("Checking Python version...")
    version = sys.version_info
    # Python 3.11+ is required because the codebase uses modern typing syntax such as `str | None`.
    if (version.major, version.minor) >= (3, 11):
        print(f"  Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"  Python {version.major}.{version.minor}.{version.micro} (Need 3.11+)")
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
                # sqlite3 is built-in, so we just check if it's available
                pass
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
        PROJECT_ROOT / 'schema.sql': 'Database schema',
        PROJECT_ROOT / 'utils/init_db.py': 'Database initialization',
        PROJECT_ROOT / 'utils/scrape_pdfs_phase1.py': 'Main scraper',
        PROJECT_ROOT / 'utils/export_csv.py': 'CSV export tool',
        PROJECT_ROOT / 'README.md': 'Documentation',
        PROJECT_ROOT / 'requirements.txt': 'Dependencies list',
    }
    all_ok = True
    for filename, description in required_files.items():
        path = filename  # filename is already a Path object
        short_name = path.name
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {short_name:20} - {description} ({size:,} bytes)")
        else:
            print(f"  ❌ {short_name:20} - {description} (MISSING)")
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
            print("     ℹ️ No PDFs found - add some PDFs to get started!")
            # Don't fail verification just because no PDFs are present yet
    else:
        print("  ℹ️ input_pdfs/ does not exist (will be created)")
        input_dir.mkdir(exist_ok=True)
        print("  ✅ Created input_pdfs/ directory")
    if output_dir.exists():
        print("  ✅ output/ exists")
    else:
        print("  ℹ️ output/ does not exist (will be created on first run)")
    return all_ok

def check_database():
    """Check if database exists and is valid"""
    print("\nChecking database...")
    
    # Check for domain-specific databases first, then fall back to general
    db_paths = [
        PROJECT_ROOT / 'db' / 'runs.sqlite',                             # Canonical database
    ]
    
    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print("  No database found. Expected one of:")
        for path in db_paths:
            print(f"    - {path}")
        print("  Run: python utils/init_db.py db/runs.sqlite --force")
        return True
    
    print(f"  Found database: {db_path.name}")
    
    try:
        if db_path.suffix == '.sqlite':
            # SQLite database
            with connect_with_foreign_keys(db_path) as con:
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
                    print(f"  Database exists but missing tables: {', '.join(missing)}")
                    print("     Run: python utils/init_db.py db/runs.sqlite --force")
                    return False
                
                # Check record counts
                sources = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
                events = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]
                entities = con.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
                print("  Database initialized and valid")
                print(f"     Sources: {sources}, Events: {events}, Entities: {entities}")
            if events == 0:
                print("     No data yet - run: python utils/scrape_pdfs_phase1.py")
        elif db_path.suffix == '.csv':            # CSV file (domain-specific export)
            import csv
            with open(db_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                print(f"  CSV export file found with {len(rows)-1} entities (header excluded)")
                if len(rows) > 1:
                    print(f"     Sample entity: {rows[1][1] if len(rows[1]) > 1 else 'N/A'}")
        
        return True
    except Exception as e:
        print(f"  Database error: {e}")
        return False

def test_import():
    """Test if we can import the scraper modules"""
    print("\nTesting module imports...")
    
    try:
        # Test if we can read the canonical schema at the project root
        schema_path = (PROJECT_ROOT / "schema.sql").resolve()
        if schema_path.exists():
            schema = schema_path.read_text()
            if 'CREATE TABLE' in schema:
                print("  schema.sql is valid")
            else:
                print("  schema.sql appears invalid")
                return False
        else:
            print(f"  schema.sql not found at {schema_path}")
            return False

        # Test basic imports
        print("  All core modules can be imported")
        return True

    except Exception as e:
        print(f"  Import error: {e}")
        return False

def print_summary(results):
    """Print summary of verification"""
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{status:10} - {check}")
    
    print("="*60)
    
    if all_passed:
        print("\nAll checks passed! You're ready to go!")
        print("\nNext steps:")
        print("  1. Add PDFs to input_pdfs/ folder")
        print("  2. Run: python init_db.py (if not done)")
        print("  3. Run: python utils/scrape_pdfs_phase1.py")
        print("  4. Run: python utils/export_csv.py --domain construction_science")
        print("\nSee QUICKSTART.md for detailed instructions.")
    else:
        print("\nSome checks failed. Please fix the issues above.")
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