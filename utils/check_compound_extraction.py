import sqlite3
from pathlib import Path

def check_compound_extraction():
    """Check what compounds were found and what's available"""
    
    print("\n" + "="*70)
    print("COMPOUND EXTRACTION ANALYSIS")
    print("="*70)
    
    # Always initialize to avoid unassigned reference
    found_compounds = []
    seed_compounds = []

    # Check what was extracted
    db_path = Path("runs/test_enhanced_seeds.sqlite")
    if not db_path.exists():
        print(f"Error: Database file not found: {db_path}")
        return
    try:
        with sqlite3.connect(db_path) as con:
            con.execute("PRAGMA foreign_keys = ON;")
            cur = con.cursor()
            print("\n📊 COMPOUNDS FOUND IN TEST SCRAPE (25 PDFs):")
            try:
                cur.execute("""
                    SELECT DISTINCT entity_name 
                    FROM entities 
                    WHERE entity_type = 'compound' 
                    ORDER BY entity_name
                """)
                found_compounds = [row[0] for row in cur.fetchall()]
            except sqlite3.OperationalError as e:
                print(f"Error: {e}")
                return
            print(f"   Total extracted: {len(found_compounds)}")
            for i, compound in enumerate(found_compounds, 1):
                print(f"      {i}. {compound}")
            if found_compounds:
                print("\n✅ YES - Your app CAN find compound names!")
            else:
                print("\n❌ NO - Your app could not find any compound names.")
    except Exception as e:
        print(f"Error: Could not open database: {e}")
        return
    print("\n📋 COMPOUNDS AVAILABLE IN SEED FILE:")
    seeds_path = Path("seeds/base/compounds.txt")
    try:
        lines = seeds_path.read_text(encoding='utf-8').split('\n')
    except (FileNotFoundError, PermissionError) as e:
        print(f"Error: Could not read seed file {seeds_path}: {e}")
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Strip inline comments
        line = line.split('#', 1)[0].strip()
        if line:
            seed_compounds.append(line)
    
    print(f"   Total in seeds: {len(seed_compounds)}")
    print("\n   Sample (first 20):")
    for i, compound in enumerate(seed_compounds[:20], 1):
        print(f"   {i:2d}. {compound}")

    if len(seed_compounds) > 20:
        print(f"   ... and {len(seed_compounds) - 20} more")

    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)

    print("\n📈 Coverage:")
    print(f"   - Seed file has: {len(seed_compounds)} compounds")
    print(f"   - Test found: {len(found_compounds)} compounds")
    if len(seed_compounds) > 0:
        rate = len(found_compounds)/len(seed_compounds)*100
        print(f"   - Detection rate: {rate:.1f}%")
    else:
        print("   - Detection rate: N/A (no seed compounds)")

    print("\n🔍 How it works:")
    print("   1. Scraper reads compounds.txt seed file")
    print("   2. Searches PDFs for exact matches (case-insensitive)")
    print("   3. Extracts compound name when found in text")
    print("   4. Tags as 'compound' entity type")

    print(f"\n💡 Why only {len(found_compounds)} found in test:")
    print("   - Test used only 25 PDFs (small sample)")
    print("   - PDFs focused on neuroscience/longevity (not all drug-focused)")
    print("   - Compounds must appear in text to be detected")
    print("   - Full corpus would find many more")

    print("\n🎯 Compounds found in test:")
    for compound in found_compounds:
        print(f"   ✓ {compound}")

    print("\n📚 Example compounds in your seed file:")
    examples = [
        "metformin", "rapamycin", "resveratrol", "nad+", "nmn",
        "spermidine", "fisetin", "quercetin", "curcumin", "berberine"
    ]
    lower_seed = {s.lower() for s in seed_compounds}
    available = [c for c in examples if c.lower() in lower_seed]
    print(f"   Available: {', '.join(available[:10])}")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    check_compound_extraction()
