#!/usr/bin/env python3
"""
Comprehensive results viewer for construction science export
"""

import csv
import json
from pathlib import Path

def show_summary():
    """Show overall summary"""
    print("=" * 80)
    print("🏗️  CONSTRUCTION SCIENCE RESULTS SUMMARY")
    print("=" * 80)
    
    # Load metadata
    meta_file = Path('output/run_meta_construction_science.json')
    if meta_file.exists():
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        print(f"📊 TOTAL STATISTICS:")
        print(f"   Events: {meta['counts']['total_events']}")
        print(f"   Entities: {meta['counts']['total_entities']}")
        print(f"   Relationships: {meta['counts']['total_relationships']}")
        print(f"   Sources: {meta['counts']['total_sources']}")
        print()
        
        print(f"🏗️  ENTITY TYPE BREAKDOWN:")
        for entity_type, count in meta['entity_type_breakdown'].items():
            print(f"   {entity_type}: {count}")
        print()
        
        print(f"📈 TOP 10 ENTITIES BY EVENT COUNT:")
        for i, entity in enumerate(meta['top_entities'][:10], 1):
            print(f"   {i:2d}. {entity['name']} ({entity['type']}) - {entity['event_count']} events, {entity['paper_count']} papers")
        print()

def show_sample_events():
    """Show sample events"""
    print("🏗️  SAMPLE EVENTS (First 5):")
    print("=" * 80)
    
    events_file = Path('output/events_export_construction_science.csv')
    if events_file.exists():
        with open(events_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                print(f"Event {i+1}: {row['event_id']}")
                print(f"  Domain: {row['domain']}")
                print(f"  Type: {row['event_type']}")
                print(f"  Stage: {row['stage']}")
                print(f"  Confidence: {row['confidence']}")
                print(f"  Outcome: {row['outcome'][:100]}...")
                print(f"  Entities: {row['entities']}")
                print(f"  Source: {row['source_id']}")
                print("-" * 40)
    else:
        print("❌ Events file not found")
    print()

def show_sample_sources():
    """Show sample sources"""
    print("🏗️  SAMPLE SOURCES (First 5):")
    print("=" * 80)
    
    sources_file = Path('output/construction_sources.csv')
    if sources_file.exists():
        with open(sources_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 5:
                    break
                print(f"Source {i+1}: {row['source_id']}")
                print(f"  File: {row['pdf_file']}")
                print(f"  Title: {row['title'][:80]}...")
                print(f"  Authors: {row['authors']}")
                print(f"  Year: {row['year']}")
                print(f"  DOI: {row['doi']}")
                print("-" * 40)
    else:
        print("❌ Sources file not found")
    print()

def show_entity_relationships():
    """Show entity relationships"""
    print("🏗️  ENTITY RELATIONSHIPS SAMPLE (First 10):")
    print("=" * 80)
    
    rel_file = Path('output/construction_event_entities.csv')
    if rel_file.exists():
        with open(rel_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            seen = set()
            count = 0
            for row in reader:
                key = f"{row['entity_type']}:{row['entity_name']}"
                if key not in seen:
                    seen.add(key)
                    print(f"{row['entity_type']}: {row['entity_name']} ({row['entity_variant']})")
                    count += 1
                    if count >= 10:
                        break
    else:
        print("❌ Relationships file not found")
    print()

def main():
    """Main function"""
    show_summary()
    show_sample_events()
    show_sample_sources()
    show_entity_relationships()
    
    print("📁 EXPORTED FILES:")
    print("=" * 80)
    output_dir = Path('output')
    for file in output_dir.glob('*.csv'):
        print(f"   📊 {file.name}")
    for file in output_dir.glob('*.json'):
        print(f"   📋 {file.name}")
    
    print()
    print("✅ All results exported successfully!")
    print("   Use these files for further analysis and reporting.")

if __name__ == "__main__":
    main()