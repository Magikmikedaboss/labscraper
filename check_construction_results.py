#!/usr/bin/env python3
import json
import sys

def check_construction_results():
    try:
        with open('output/run_meta_construction_science.json', 'r') as f:
            data = json.load(f)
        
        print("📊 Construction Science Export Results:")
        print(f"   Events Processed: {data['counts']['total_events']}")
        print(f"   Primary Entities: {data['counts']['primary_entities']}")
        print(f"   Overlay Aliases: {data['overlay_aliases_count']}")
        print(f"   Confidence High: {data['confidence_distribution']['high']}")
        print(f"   Confidence Med: {data['confidence_distribution']['med']}")
        print(f"   Confidence Low: {data['confidence_distribution']['low']}")
        
        print("\n🎯 Top 10 Entities:")
        for i, entity in enumerate(data['top_entities'][:10], 1):
            print(f"   {i}. {entity['name']} ({entity['type']}): {entity['event_count']} events")
            
    except FileNotFoundError:
        print("❌ File not found: output/run_meta_construction_science.json")
        print("Make sure the export has been run successfully.")
    except Exception as e:
        print(f"❌ Error reading results: {e}")

if __name__ == "__main__":
    check_construction_results()