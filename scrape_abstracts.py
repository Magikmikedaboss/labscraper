#!/usr/bin/env python3
"""
Hybrid RSS + Web Scraping System
Extracts research insights from ASCE abstracts without downloading PDFs
"""

import feedparser
import requests
import re
import sqlite3
import argparse
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
import json

# Import functions from utils/run_engine.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "utils"))

# Import chunk_sentences function that's missing
def chunk_sentences(text):
    """Simple sentence chunking for abstract processing"""
    import re
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]

# Import functions from utils/run_engine.py
try:
    from run_engine import (
        extract_metadata, guess_stage, guess_section,
        extract_entities, extract_quantitative_data,
        detect_method_tags, detect_failure_reason, detect_decision, detect_outcome,
        classify_event_type, evidence_strength, confidence_score,
        suggested_keep, normalize_event_key,
        upsert_source, insert_document, insert_chunk, insert_event,
        link_event_entity, link_event_tag, insert_measurement, upsert_entity,
        now_iso, sha16, sha64, RESEARCH_DOMAIN,
        FAILURE_PHRASES, DECISION_PHRASES, METHOD_TAGS
    )
    print("✅ Successfully imported run_engine functions")
except ImportError:
    print("⚠️  Could not import run_engine functions - using mock functions for testing")
    
    # Mock functions for testing
    def extract_metadata(url, abstract_text):
        return {"title": "Test Paper", "authors": ["Test Author"], "year": "2023"}
    
    def guess_stage(text):
        return "unknown"
    
    def guess_section(text):
        return "abstract"
    
    def extract_entities(text, domain):
        return []
    
    def extract_quantitative_data(text):
        return []
    
    def detect_method_tags(text):
        return []
    
    def detect_failure_reason(text):
        return None
    
    def detect_decision(text):
        return None, None
    
    def detect_outcome(text):
        return "unknown"
    
    def classify_event_type(text, tags, failure_reason, decision_taken):
        return "other"
    
    def evidence_strength(text):
        return "low"
    
    def confidence_score(has_entities, tags, failure_reason, decision_taken, has_measurements, text):
        return 0.5
    
    def suggested_keep(conf, event_type, failure_reason, decision_taken, tags):
        return 1
    
    def normalize_event_key(event_type, ents, page_idx, sent):
        return f"{event_type}_{page_idx}_{hash(sent) % 1000}"
    
    def upsert_source(con, source_id, filename, metadata):
        return source_id
    
    def insert_document(con, source_id, path, file_hash):
        return 1
    
    def insert_chunk(con, source_id, doc_id, page_idx, section, text):
        return 1
    
    def insert_event(con, source_id, doc_id, chunk_id, page_number, domain, event_type, study_stage, biological_system, application_area, outcome, failure_reason, decision_taken, decision_driver, evidence_snippet, evidence_strength_v, confidence_v):
        return 1
    
    def link_event_entity(con, event_id, entity_id, role):
        pass
    
    def link_event_tag(con, event_id, tag):
        pass
    
    def insert_measurement(con, event_id, measurement):
        pass
    
    def upsert_entity(con, entity_type, entity_name, entity_variant, role):
        return 1
    
    def now_iso():
        from datetime import datetime
        return datetime.now().isoformat()
    
    def sha16(text):
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def sha64(text):
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()
    
    RESEARCH_DOMAIN = "test"
    FAILURE_PHRASES = {}
    DECISION_PHRASES = {}
    METHOD_TAGS = {}

# Default paths
DB_PATH = Path("db") / "runs.sqlite"
FEEDS_CONFIG = Path("config") / "feeds.json"

def load_feeds_config():
    """Load RSS feeds configuration from JSON file"""
    if not FEEDS_CONFIG.exists():
        print(f"⚠️  RSS feeds config not found: {FEEDS_CONFIG}")
        return {"feeds": []}
    
    with open(FEEDS_CONFIG, 'r') as f:
        return json.load(f)

def extract_abstract_from_asce_page(abstract_url):
    """Extract abstract text from ASCE journal page"""
    try:
        print(f"  🌐 Scraping abstract: {abstract_url}")
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(abstract_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html = response.text
        
        # Extract abstract using regex patterns
        abstract_patterns = [
            r'<div[^>]*class="abstract"[^>]*>(.*?)</div>',
            r'<div[^>]*class="abstractSection"[^>]*>(.*?)</div>',
            r'<p[^>]*class="abstract"[^>]*>(.*?)</p>',
            r'<div[^>]*id="abstract"[^>]*>(.*?)</div>',
            r'Abstract</h2>\s*<p>(.*?)</p>',
            r'ABSTRACT</h2>\s*<p>(.*?)</p>'
        ]
        
        abstract_text = ""
        for pattern in abstract_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                abstract_text = match.group(1)
                # Clean up HTML tags
                abstract_text = re.sub(r'<[^>]+>', '', abstract_text)
                abstract_text = re.sub(r'\s+', ' ', abstract_text).strip()
                if abstract_text and len(abstract_text) > 50:  # Ensure it's a real abstract
                    break
        
        if abstract_text:
            print(f"  ✅ Extracted abstract ({len(abstract_text)} chars)")
            return abstract_text
        else:
            print(f"  ⚠️  No abstract found on page")
            return None
            
    except Exception as e:
        print(f"  ❌ Error scraping {abstract_url}: {e}")
        return None

def process_abstract_with_engine(abstract_url, abstract_text, domain, db_path):
    """Process abstract using the existing engine functions"""
    try:
        # Create stable source ID based on URL
        source_id = sha16(abstract_url)
        file_hash = sha64(abstract_url)
        
        events_count = 0
        seen_events = set()
        
        with sqlite3.connect(db_path) as con:
            # Extract metadata from URL
            metadata = {
                "title": f"ASCE Abstract: {abstract_url.split('/')[-1][:50]}",
                "authors": ["ASCE Journal"],
                "year": "2023",
                "url": abstract_url
            }
            
            upsert_source(con, source_id, abstract_url, metadata)
            doc_id = insert_document(con, source_id, abstract_url, file_hash)
            
            # Process abstract as a single "page"
            page_idx = 1
            section = "abstract"
            chunk_id = insert_chunk(con, source_id, doc_id, page_idx, section, abstract_text)
            
            for sent in chunk_sentences(abstract_text):
                s_l = sent.lower()
                
                # Check for signals
                has_signal = (
                    any(p in s_l for lst in FAILURE_PHRASES.values() for p in lst) or
                    any(p in s_l for lst in DECISION_PHRASES.values() for p in lst) or
                    any(p in s_l for lst in METHOD_TAGS.values() for p in lst)
                )
                if not has_signal:
                    continue
                
                # Process sentence
                tags = detect_method_tags(s_l)
                failure_reason = detect_failure_reason(s_l)
                decision_taken, decision_driver = detect_decision(s_l)
                outcome = detect_outcome(s_l)
                stage = guess_stage(s_l)
                event_type = classify_event_type(s_l, tags, failure_reason, decision_taken)
                strength = evidence_strength(s_l)
                
                ents = extract_entities(sent, domain)
                measurements = extract_quantitative_data(sent)
                
                conf = confidence_score(bool(ents), tags, failure_reason, decision_taken, bool(measurements), s_l)
                keep = suggested_keep(conf, event_type, failure_reason, decision_taken, tags)
                
                if keep == 0 and event_type == "other":
                    continue
                
                event_key = normalize_event_key(event_type, ents, page_idx, sent)
                if event_key in seen_events:
                    continue
                seen_events.add(event_key)
                
                # Insert event
                bio_sys = None
                if "serum" in tags:
                    bio_sys = "serum/plasma"
                elif "organoid" in s_l:
                    bio_sys = "organoid"
                elif "cell line" in s_l or re.search(r'\bcell culture\b|\bcell lines?\b', s_l):
                    bio_sys = "cells"
                
                event_id = insert_event(
                    con=con,
                    source_id=source_id,
                    doc_id=doc_id,
                    chunk_id=chunk_id,
                    page_number=page_idx,
                    domain=domain,
                    event_type=event_type,
                    study_stage=stage,
                    biological_system=bio_sys,
                    application_area=None,
                    outcome=outcome,
                    failure_reason=failure_reason,
                    decision_taken=decision_taken,
                    decision_driver=decision_driver,
                    evidence_snippet=sent,
                    evidence_strength_v=strength,
                    confidence_v=conf,
                )
                
                # Link entities and tags
                for t in tags:
                    link_event_tag(con, event_id, t)
                
                for e in ents:
                    entity_id = upsert_entity(
                        con,
                        e["entity_type"],
                        e["entity_name"],
                        e.get("entity_variant"),
                        None
                    )
                    link_event_entity(con, event_id, entity_id, e.get("role", "unknown"))
                
                # Insert measurements
                for m in measurements:
                    insert_measurement(con, event_id, m)
                
                events_count += 1
        
        return events_count
        
    except Exception as e:
        print(f"  ❌ Error processing abstract {abstract_url}: {e}")
        return 0

def main():
    """Main hybrid RSS + web scraping function"""
    parser = argparse.ArgumentParser(description='Hybrid RSS + Web Scraping System')
    parser.add_argument('--feeds-config', type=Path, default=FEEDS_CONFIG,
                       help='Path to RSS feeds configuration JSON file')
    parser.add_argument('--db-path', type=Path, default=DB_PATH,
                       help='Output database path')
    parser.add_argument('--domain', type=str, default="construction_science",
                       help='Domain for processing (default: construction_science)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without actually processing')
    parser.add_argument('--scrape-only', action='store_true',
                       help='Only process abstracts, skip PDF downloads')
    
    args = parser.parse_args()
    
    # Load feeds configuration
    feeds_config = load_feeds_config()
    
    # Ensure database directory exists
    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("🌐 HYBRID RSS + WEB SCRAPING SYSTEM")
    print("=" * 60)
    print(f"Database: {args.db_path}")
    print(f"Feeds config: {args.feeds_config}")
    print(f"Domain: {args.domain}")
    print()
    
    total_processed = 0
    total_events = 0
    
    # Process each feed
    for feed_config in feeds_config.get('feeds', []):
        if not feed_config.get('enabled', True):
            print(f"⏭️  Skipping disabled feed: {feed_config['name']}")
            continue
        
        feed_url = feed_config['url']
        domain = args.domain
        
        print(f"📡 Processing feed: {feed_config['name']}")
        print(f"   URL: {feed_url}")
        print(f"   Domain: {domain}")
        
        # Get entries from feed
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.entries
            print(f"   Found {len(entries)} entries")
        except Exception as e:
            print(f"   ❌ Error parsing feed: {e}")
            continue
        
        if not entries:
            print("   No entries found, skipping...")
            continue
        
        # Process each entry
        feed_processed = 0
        feed_events = 0
        
        for entry in entries:
            title = entry.get('title', 'Unknown')
            published = entry.get('published', '')
            
            print(f"   📄 {title}")
            if published:
                print(f"      Published: {published}")
            
            # Find abstract links
            abstract_links = []
            
            # Check entry links
            for link in entry.get('links', []):
                href = link.get('href', '')
                if href and ('doi.org' in href or 'ascelibrary.org' in href):
                    abstract_links.append(href)
            
            # Check entry summary for links
            summary = entry.get('summary', '')
            doi_matches = re.findall(r'https?://doi\.org/[^\s<>"\']+', summary, re.IGNORECASE)
            abstract_links.extend(doi_matches)
            
            # Check entry content for links
            for content in entry.get('content', []):
                content_value = content.get('value', '')
                doi_matches = re.findall(r'https?://doi\.org/[^\s<>"\']+', content_value, re.IGNORECASE)
                abstract_links.extend(doi_matches)
            
            if not abstract_links:
                print(f"      ⚠️  No abstract links found")
                continue
            
            # Process each abstract link
            for abstract_url in abstract_links[:1]:  # Process first link only to avoid duplicates
                print(f"      🔗 Abstract: {abstract_url}")
                
                if args.dry_run:
                    print("      [DRY RUN] Would scrape and process abstract")
                    feed_processed += 1
                    continue
                
                # Extract abstract text
                abstract_text = extract_abstract_from_asce_page(abstract_url)
                if not abstract_text:
                    continue
                
                # Process abstract
                events_count = process_abstract_with_engine(abstract_url, abstract_text, domain, args.db_path)
                if events_count > 0:
                    feed_processed += 1
                    feed_events += events_count
                    print(f"      ✅ Processed: {events_count} events")
                else:
                    print(f"      ⚠️  No events extracted")
        
        total_processed += feed_processed
        total_events += feed_events
        
        print(f"   Summary: {feed_processed} processed, {feed_events} events extracted")
        print()
        
        # Be respectful to servers
        time.sleep(2)
    
    print("=" * 60)
    print("HYBRID PROCESSING COMPLETE")
    print(f"Total processed: {total_processed}")
    print(f"Total events extracted: {total_events}")
    print(f"Database: {args.db_path}")
    
    if args.dry_run:
        print("\n⚠️  This was a dry run - no actual scraping or processing occurred")

if __name__ == "__main__":
    main()