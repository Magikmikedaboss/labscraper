import sqlite3
from pathlib import Path

DB_PATH = Path("runs") / "peptide_intel.sqlite"

def main():
    if not DB_PATH.exists():
        print(f"\u274c Database file not found: {DB_PATH}")
        return
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        print("\n" + "="*60)
        print("TARGET EXTRACTION INVESTIGATION")
        print("="*60)
        # Check for target context words in events
        TARGET_CONTEXT_WORDS = [
            "agonist", "antagonist", "inhibitor", "activator",
            "binding", "affinity", "receptor", "pathway", "signaling",
            "target", "modulator", "blocker",
        ]
        print("\n1. Checking for target context words in events...")
        print("-" * 60)

        for word in TARGET_CONTEXT_WORDS:
            cur.execute("""
                SELECT COUNT(*)
                FROM research_events
                WHERE LOWER(evidence_snippet) LIKE ?
            """, (f'%{word}%',))
        # ...existing code for the rest of the script, indented inside main()...


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
