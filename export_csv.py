import sqlite3
from pathlib import Path
import csv

DB_PATH = Path("output") / "peptide_intel.sqlite"
EVENTS_CSV = Path("output") / "events_export.csv"
CANDIDATES_CSV = Path("output") / "candidates_export.csv"
MEASUREMENTS_CSV = Path("output") / "measurements_export.csv"
RELATIONSHIPS_CSV = Path("output") / "relationships_export.csv"

def export_events(con):
    """Export research events with entity information"""
    print("Exporting events...")
    
    # Enhanced query that includes entities
    # FIX 3: Use semicolon as delimiter for consistency
    rows = con.execute("""
      SELECT
        e.research_domain,
        e.event_type,
        e.study_stage,
        e.biological_system,
        e.outcome,
        e.failure_reason,
        e.decision_taken,
        e.evidence_strength,
        e.confidence,
        e.source_id,
        s.pdf_file,
        s.title,
        s.authors,
        s.year,
        s.doi,
        e.page_number,
        e.evidence_snippet,
        GROUP_CONCAT(DISTINCT ent.entity_name || ' (' || ent.entity_type || ')') as entities,
        GROUP_CONCAT(DISTINCT t.tag) as tags
      FROM research_events e
      JOIN sources s ON s.source_id = e.source_id
      LEFT JOIN event_entities ee ON ee.event_id = e.event_id
      LEFT JOIN entities ent ON ent.entity_id = ee.entity_id
      LEFT JOIN event_tags et ON et.event_id = e.event_id
      LEFT JOIN tags t ON t.tag = et.tag
      GROUP BY e.event_id
      ORDER BY
        CASE e.confidence WHEN 'high' THEN 0 WHEN 'med' THEN 1 ELSE 2 END,
        CASE e.evidence_strength WHEN 'strong' THEN 0 WHEN 'moderate' THEN 1 ELSE 2 END,
        s.pdf_file, e.page_number
    """).fetchall()

    EVENTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(EVENTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "research_domain", "event_type", "study_stage", "biological_system",
            "outcome", "failure_reason", "decision_taken",
            "evidence_strength", "confidence",
            "source_id", "pdf_file", "title", "authors", "year", "doi",
            "page_number", "evidence_snippet", "entities", "tags"
        ])
        w.writerows(rows)

    print(f"✅ Exported {len(rows)} events to: {EVENTS_CSV.resolve()}")
    return len(rows)

def export_candidates(con):
    """Export entity-focused view showing peptides/candidates and their research history"""
    print("Exporting candidates...")
    
    # FIX 3: Use semicolon as delimiter for consistency
    rows = con.execute("""
      SELECT
        ent.entity_type,
        ent.entity_name,
        ent.entity_variant,
        COUNT(DISTINCT e.event_id) as total_events,
        COUNT(DISTINCT CASE WHEN e.confidence = 'high' THEN e.event_id END) as high_conf_events,
        GROUP_CONCAT(DISTINCT e.outcome) as outcomes,
        GROUP_CONCAT(DISTINCT e.failure_reason) as failure_reasons,
        GROUP_CONCAT(DISTINCT e.decision_taken) as decisions,
        GROUP_CONCAT(DISTINCT e.event_type) as event_types,
        GROUP_CONCAT(DISTINCT e.study_stage) as study_stages,
        COUNT(DISTINCT s.source_id) as num_papers,
        GROUP_CONCAT(DISTINCT s.pdf_file) as papers,
        MIN(s.year) as first_mentioned_year,
        MAX(s.year) as last_mentioned_year
      FROM entities ent
      JOIN event_entities ee ON ee.entity_id = ent.entity_id
      JOIN research_events e ON e.event_id = ee.event_id
      JOIN sources s ON s.source_id = e.source_id
      GROUP BY ent.entity_id
      ORDER BY total_events DESC, high_conf_events DESC
    """).fetchall()

    CANDIDATES_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(CANDIDATES_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "entity_type", "entity_name", "entity_variant",
            "total_events", "high_conf_events",
            "outcomes", "failure_reasons", "decisions", "event_types", "study_stages",
            "num_papers", "papers", "first_mentioned_year", "last_mentioned_year"
        ])
        w.writerows(rows)

    print(f"✅ Exported {len(rows)} candidates to: {CANDIDATES_CSV.resolve()}")
    return len(rows)

def export_measurements(con):
    """Export quantitative measurements"""
    print("Exporting measurements...")
    
    # FIX 3: Use semicolon as delimiter for consistency
    rows = con.execute("""
      SELECT
        m.measurement_type,
        m.value,
        m.unit,
        m.context,
        e.event_type,
        e.outcome,
        e.study_stage,
        s.pdf_file,
        s.title,
        e.page_number,
        GROUP_CONCAT(DISTINCT ent.entity_name) as entities
      FROM quantitative_measurements m
      JOIN research_events e ON e.event_id = m.event_id
      JOIN sources s ON s.source_id = e.source_id
      LEFT JOIN event_entities ee ON ee.event_id = e.event_id
      LEFT JOIN entities ent ON ent.entity_id = ee.entity_id
      GROUP BY m.measurement_id
      ORDER BY m.measurement_type, m.value
    """).fetchall()

    if rows:
        MEASUREMENTS_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(MEASUREMENTS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "measurement_type", "value", "unit", "context",
                "event_type", "outcome", "study_stage",
                "pdf_file", "title", "page_number", "entities"
            ])
            w.writerows(rows)

        print(f"✅ Exported {len(rows)} measurements to: {MEASUREMENTS_CSV.resolve()}")
    else:
        print("ℹ️  No measurements found to export")
    
    return len(rows)

def export_relationships(con):
    """Export entity relationships"""
    print("Exporting relationships...")
    
    rows = con.execute("""
      SELECT
        e1.entity_name as entity_1,
        e1.entity_type as entity_1_type,
        r.relationship_type,
        e2.entity_name as entity_2,
        e2.entity_type as entity_2_type,
        r.confidence,
        ev.event_type,
        ev.outcome,
        s.pdf_file,
        s.title,
        ev.page_number,
        ev.evidence_snippet
      FROM entity_relationships r
      JOIN entities e1 ON e1.entity_id = r.entity_id_1
      JOIN entities e2 ON e2.entity_id = r.entity_id_2
      LEFT JOIN research_events ev ON ev.event_id = r.event_id
      LEFT JOIN sources s ON s.source_id = ev.source_id
      ORDER BY r.relationship_type, r.confidence DESC
    """).fetchall()

    if rows:
        RELATIONSHIPS_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(RELATIONSHIPS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "entity_1", "entity_1_type", "relationship_type",
                "entity_2", "entity_2_type", "confidence",
                "event_type", "outcome", "pdf_file", "title",
                "page_number", "evidence_snippet"
            ])
            w.writerows(rows)

        print(f"✅ Exported {len(rows)} relationships to: {RELATIONSHIPS_CSV.resolve()}")
    else:
        print("ℹ️  No relationships found to export")
    
    return len(rows)

def print_summary(con):
    """Print database summary statistics"""
    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)
    
    # Count sources
    sources = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    print(f"📄 Sources (papers): {sources}")
    
    # Count events by confidence
    events_high = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'high'").fetchone()[0]
    events_med = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'med'").fetchone()[0]
    events_low = con.execute("SELECT COUNT(*) FROM research_events WHERE confidence = 'low'").fetchone()[0]
    print(f"🔬 Events: {events_high + events_med + events_low} total")
    print(f"   - High confidence: {events_high}")
    print(f"   - Med confidence: {events_med}")
    print(f"   - Low confidence: {events_low}")
    
    # Count entities by type
    entities = con.execute("""
        SELECT entity_type, COUNT(*) as cnt 
        FROM entities 
        GROUP BY entity_type 
        ORDER BY cnt DESC
    """).fetchall()
    print(f"🧬 Entities: {sum(e[1] for e in entities)} total")
    for etype, count in entities:
        print(f"   - {etype}: {count}")
    
    # Count measurements
    measurements = con.execute("SELECT COUNT(*) FROM quantitative_measurements").fetchone()[0]
    if measurements > 0:
        print(f"📊 Quantitative measurements: {measurements}")
    
    # Count relationships
    relationships = con.execute("SELECT COUNT(*) FROM entity_relationships").fetchone()[0]
    if relationships > 0:
        print(f"🔗 Entity relationships: {relationships}")
    
    # Top event types
    print("\n📈 Top Event Types:")
    top_events = con.execute("""
        SELECT event_type, COUNT(*) as cnt 
        FROM research_events 
        GROUP BY event_type 
        ORDER BY cnt DESC 
        LIMIT 5
    """).fetchall()
    for etype, count in top_events:
        print(f"   - {etype}: {count}")
    
    print("="*60 + "\n")

def main():
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH.resolve()}\nRun scrape_pdfs.py first!")

    con = sqlite3.connect(DB_PATH)
    try:
        # Print summary first
        print_summary(con)
        
        # Export all data
        events_count = export_events(con)
        candidates_count = export_candidates(con)
        measurements_count = export_measurements(con)
        relationships_count = export_relationships(con)
        
        print("\n" + "="*60)
        print("EXPORT COMPLETE")
        print("="*60)
        print(f"✅ Events exported: {events_count}")
        print(f"✅ Candidates exported: {candidates_count}")
        print(f"✅ Measurements exported: {measurements_count}")
        print(f"✅ Relationships exported: {relationships_count}")
        print("\nYou can now open these CSV files in Excel or your favorite analysis tool!")
        print("="*60)
        
    finally:
        con.close()

if __name__ == "__main__":
    main()
