import sqlite3
from pathlib import Path

DB_PATH = Path("output") / "peptide_intel.sqlite"

def check_confidence_distribution():
    """Check confidence score distribution"""
    with sqlite3.connect(DB_PATH) as con:
        total = con.execute("SELECT COUNT(*) FROM research_events").fetchone()[0]
        high = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'high'").fetchone()[0]
        med = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'med'").fetchone()[0]
        low = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'low'").fetchone()[0]

        print("\nTotal events:", total)
        if total == 0:
            print(f"High confidence: {high} (0.0%)")
            print(f"Med confidence: {med} (0.0%)")
            print(f"Low confidence: {low} (0.0%)")
        else:
            print(f"High confidence: {high} ({high/total*100:.1f}%)")
            print(f"Med confidence: {med} ({med/total*100:.1f}%)")
            print(f"Low confidence: {low} ({low/total*100:.1f}%)")


        print("\n" + "="*60)
        print("SAMPLE HIGH CONFIDENCE EVENTS")
        print("="*60)
        high_events = con.execute("""
            SELECT event_type, stage AS study_stage, evidence_snippet
            FROM research_events
            WHERE confidence = 'high'
            LIMIT 5
        """).fetchall()


        print("\nHigh confidence events:")
        print("-"*30)
        for i, (etype, stage, snippet) in enumerate(high_events, 1):
            snippet_text = snippet or ""
            print(f"\n{i}. {etype} ({stage})")
            if len(snippet_text) > 150:
                print(f"   {snippet_text[:150]}...")
            elif snippet_text:
                print(f"   {snippet_text}")
            else:
                print("")

        # Sample med confidence events
        print("\n" + "="*60)
        print("SAMPLE MED CONFIDENCE EVENTS")
        print("="*60)

        med_events = con.execute("""
            SELECT event_type, stage AS study_stage, evidence_snippet
            FROM research_events
            WHERE confidence = 'med'
            LIMIT 5
        """).fetchall()

        for i, (etype, stage, snippet) in enumerate(med_events, 1):
            snippet_text = snippet or ""
            print(f"\n{i}. {etype} ({stage})")
            if len(snippet_text) > 150:
                print(f"   {snippet_text[:150]}...")
            elif snippet_text:
                print(f"   {snippet_text}")
            else:
                print("")
    # Removed duplicate med_events loop and redundant con.close()

if __name__ == "__main__":
    check_confidence_distribution()
