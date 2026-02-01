#!/usr/bin/env python3
import json

def check_construction_results():
    try:
        with open('output/run_meta_construction_science.json', 'r') as f:
            data = json.load(f)
        
        print("📊 Construction Science Export Results:")
        
        # Defensive access to nested dictionaries with defaults
        counts = data.get('counts', {})
        total_events = counts.get('total_events', 0)
        primary_entities = counts.get('primary_entities', 0)
        overlay_aliases_count = data.get('overlay_aliases_count', 0)
        
        confidence = data.get('confidence_distribution', {})
        confidence_high = confidence.get('high', 0)
        confidence_med = confidence.get('med', 0)
        confidence_low = confidence.get('low', 0)
        
        print(f"   Events Processed: {total_events}")
        print(f"   Primary Entities: {primary_entities}")
        print(f"   Overlay Aliases: {overlay_aliases_count}")
        print(f"   Confidence High: {confidence_high}")
        print(f"   Confidence Med: {confidence_med}")
        print(f"   Confidence Low: {confidence_low}")
        
        print("\n🎯 Top 10 Entities:")
        top_entities = data.get('top_entities', [])
        for i, entity in enumerate(top_entities[:10], 1):
            entity_name = entity.get('name', 'Unknown')
            entity_type = entity.get('type', 'Unknown')
            event_count = entity.get('event_count', 0)
            print(f"   {i}. {entity_name} ({entity_type}): {event_count} events")
            
    except FileNotFoundError:
        print("❌ File not found: output/run_meta_construction_science.json")
        print("Make sure the export has been run successfully.")
    except Exception as e:
        print(f"❌ Error reading results: {e}")

if __name__ == "__main__":
    check_construction_results()
