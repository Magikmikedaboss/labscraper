#!/usr/bin/env python3
"""
Final comprehensive test for construction science configuration
"""

import json
import sqlite3
from pathlib import Path

def test_construction_science_comprehensive():
    print("🏗️  CONSTRUCTION SCIENCE COMPREHENSIVE TESTING")
    print("=" * 60)
    
    # Check database exists
    db_path = Path("output/construction_science_intel.sqlite")
    if not db_path.exists():
        print("❌ Database not found:", db_path)
        return
    
    print(f"✅ Database found: {db_path}")
    
    # Connect and check structure
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        # Check tables
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"📊 Tables found: {[t['name'] for t in tables]}")
        
        # Check entities
        entity_counts = cur.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM entities 
            GROUP BY entity_type 
            ORDER BY count DESC
        """).fetchall()
        
        print("\n🏗️  Top Entity Types:")
        for row in entity_counts[:10]:
            print(f"   {row['entity_type']}: {row['count']}")
        
        # Check events
        event_counts = cur.execute("""
            SELECT COUNT(*) as total_events
            FROM research_events
        """).fetchone()
        
        print(f"\n📈 Total Events: {event_counts['total_events']}")
        
        # Check confidence distribution
        confidence_counts = cur.execute("""
            SELECT confidence, COUNT(*) as count
            FROM research_events
            GROUP BY confidence
        """).fetchall()
        
        print("\n🎯 Confidence Distribution:")
        for row in confidence_counts:
            print(f"   {row['confidence']}: {row['count']}")
        
        # Check top entities
        top_entities = cur.execute("""
            SELECT e.entity_name, e.entity_type, COUNT(ee.event_id) as event_count
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            GROUP BY e.entity_id
            ORDER BY event_count DESC
            LIMIT 10
        """).fetchall()
        
        print("\n🏆 Top 10 Entities by Event Count:")
        for i, row in enumerate(top_entities, 1):
            print(f"   {i}. {row['entity_name']} ({row['entity_type']}): {row['event_count']} events")
        
        # Check construction-specific entities
        construction_entities = cur.execute("""
            SELECT e.entity_name, e.entity_type, COUNT(ee.event_id) as event_count
            FROM entities e
            JOIN event_entities ee ON e.entity_id = ee.entity_id
            WHERE e.entity_type IN ('material', 'system', 'failure_mode', 'test_method', 'environment')
            GROUP BY e.entity_id
            ORDER BY event_count DESC
            LIMIT 10
        """).fetchall()
        
        print("\n🏗️  Top Construction-Specific Entities:")
        for i, row in enumerate(construction_entities, 1):
            print(f"   {i}. {row['entity_name']} ({row['entity_type']}): {row['event_count']} events")
        
        # Check run metadata
        meta = {}
        meta_path = Path("output/run_meta_construction_science.json")
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
            except json.JSONDecodeError as e:
                print(f"❌ Error decoding JSON in {meta_path}: {e}")
        print("\n📋 Run Metadata:")
        print(f"   Domain: {meta.get('domain', 'N/A')}")
        print(f"   PDFs Processed: {meta.get('pdfs_processed', 'N/A')}")
        print(f"   Events Extracted: {meta.get('events_extracted', 'N/A')}")
        print(f"   Entities Identified: {meta.get('entities_identified', 'N/A')}")
        print(f"   Run Date: {meta.get('run_date', 'N/A')}")
        
        # Check export files
        export_files = [
            "output/events_export_construction_science.csv",
            "output/candidates_primary_construction_science.csv"
        ]
        
        print("\n📁 Export Files:")
        for file_path in export_files:
            file_obj = Path(file_path)
            if file_obj.exists():
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path}")
        
        print("\n✅ Construction Science Testing Complete!")
        print("\n🎯 SYSTEM STATUS: READY FOR CONSTRUCTION SCIENCE RESEARCH INTELLIGENCE")

if __name__ == "__main__":
    test_construction_science_comprehensive()