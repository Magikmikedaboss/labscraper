import sqlite3
from pathlib import Path

DB_PATH = Path("output") / "peptide_intel.sqlite"

def check_confidence_distribution():
    """Check confidence score distribution"""
    con = sqlite3.connect(DB_PATH)
    
    print("\n" + "="*60)
    print("CONFIDENCE DISTRIBUTION")
    print("="*60)
    
    # Overall distribution
    total = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]
    high = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'high'").fetchone()[0]
    med = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'med'").fetchone()[0]
    low = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'low'").fetchone()[0]
    
    print(f"\nTotal Events: {total}")
    def percent(count):
        return (count/total*100) if total else 0
    print(f"  High: {high} ({percent(high):.1f}%)")
    print(f"  Med: {med} ({percent(med):.1f}%)")
    print(f"  Low: {low} ({percent(low):.1f}%)")
    
    # Sample high confidence events
    print("\n" + "="*60)
    print("SAMPLE HIGH CONFIDENCE EVENTS")
    print("="*60)
    
    high_events = con.execute("""
        SELECT event_type, study_stage, evidence_snippet
        FROM research_events
        WHERE confidence = 'high'
        LIMIT 5
    """).fetchall()
    
    for i, (etype, stage, snippet) in enumerate(high_events, 1):
        snippet_text = snippet or ""
        print(f"\n{i}. {etype} ({stage})")
        print(f"   {snippet_text[:150]}...")
    
    # Sample med confidence events
    print("\n" + "="*60)
    print("SAMPLE MED CONFIDENCE EVENTS")
    print("="*60)
    
    med_events = con.execute("""
        SELECT event_type, study_stage, evidence_snippet
        FROM research_events
        WHERE confidence = 'med'
        LIMIT 5
    """).fetchall()
    
    for i, (etype, stage, snippet) in enumerate(med_events, 1):
        snippet_text = snippet or ""
        print(f"\n{i}. {etype} ({stage})")
        print(f"   {snippet_text[:150]}...")
    
    con.close()

if __name__ == "__main__":
    check_confidence_distribution()
