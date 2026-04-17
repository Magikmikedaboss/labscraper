#!/usr/bin/env python3
"""
RSS Feed Ingestion System
Downloads and processes RSS feeds, extracts PDFs, and processes them through the pipeline.
"""

import feedparser
import requests
import hashlib
import sqlite3
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import pdfplumber

# Import functions from utils/run_engine.py
import sys
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from utils.validators import (
    ValidationError,
    validate_database,
    validate_directory,
    validate_domain_name,
    validate_feed_config,
    validate_file_path,
)

# Import chunk_sentences function that's missing
def chunk_sentences(text):
    """Simple sentence chunking for RSS processing"""
    import re
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]

# Import functions from utils/run_engine.py
try:
    from utils.metadata_utils import extract_metadata
    from utils.run_engine import (
        guess_stage, guess_section,
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
    def extract_metadata(pdf_path, pdf):
        return {"title": "Test Paper", "authors": ["Test Author"], "year": "2023"}
    
    def guess_stage(text):
        return "unknown"
    
    def guess_section(text):
        return "unknown"
    
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
    
    from utils.metadata_utils import extract_metadata
    from utils.run_engine import (
        guess_stage, guess_section,
        extract_entities, extract_quantitative_data,
        detect_method_tags, detect_failure_reason, detect_decision, detect_outcome,
        classify_event_type, evidence_strength, confidence_score,
        suggested_keep, normalize_event_key,
        upsert_source, insert_document, insert_chunk, insert_event,
        link_event_entity, link_event_tag, insert_measurement, upsert_entity,
        now_iso, sha16, sha64, RESEARCH_DOMAIN,
        FAILURE_PHRASES, DECISION_PHRASES, METHOD_TAGS
    )
                    "url": "http://export.arxiv.org/rss/q-bio.BM",
                    "domain": "methods_tooling", 
                    "enabled": True
                }
            ]
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        print(f"✅ Created default config at {config_path}")
        return validate_feed_config(default_config)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return validate_feed_config(json.load(f))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as err:
        raise ValidationError(f"Failed to load config {config_path}: {err}") from err

def get_pdf_links_from_feed(feed_url):
    """Extract PDF links from RSS feed entries"""
    try:
        feed = feedparser.parse(feed_url)
        pdf_links = []
        
        for entry in feed.entries:
            # Look for PDF links in various places
            links = []
            
            # Check entry links (arXiv feeds have PDF links here)
            for link in entry.get('links', []):
                href = link.get('href', '')
                if href:
                    # For arXiv, look for PDF links specifically
                    if '.pdf' in href.lower():
                        links.append(href)
                    # Also check for arXiv PDF pattern
                    elif 'arxiv.org' in href:
                        # Parse URL and normalize to PDF format
                        parsed = urlparse(href)
                        path = parsed.path
                        
                        # Ensure path has /pdf/ and ends with .pdf
                        if '/abs/' in path:
                            path = path.replace('/abs/', '/pdf/')
                        elif '/pdf/' not in path:
                            path = path.rstrip('/') + '/pdf/'
                        
                        # Ensure path ends with .pdf
                        if not path.endswith('.pdf'):
                            path += '.pdf'
                        
                        # Reconstruct URL preserving query and fragment
                        pdf_url = parsed._replace(path=path).geturl()
                        links.append(pdf_url)
            
            # Check entry summary for PDF links
            summary = entry.get('summary', '')
            pdf_matches = re.findall(r'https?://[^\s<>"\']*.pdf', summary, re.IGNORECASE)
            links.extend(pdf_matches)
            
            # Check entry content for PDF links
            for content in entry.get('content', []):
                content_value = content.get('value', '')
                pdf_matches = re.findall(r'https?://[^\s<>"\']*.pdf', content_value, re.IGNORECASE)
                links.extend(pdf_matches)
            
            # Process found links
            for link in links:
                # Clean up the link
                link = link.strip()
                if link and not link.startswith('#'):
                    # Handle relative URLs
                    if not link.startswith('http'):
                        link = urljoin(feed_url, link)
                    
                    pdf_links.append({
                        'url': link,
                        'title': entry.get('title', ''),
                        'published': entry.get('published', ''),
                        'summary': entry.get('summary', '')[:200]
                    })
        
        return pdf_links
    except Exception as e:
        print(f"❌ Error parsing feed {feed_url}: {e}")
        return []

def download_pdf(pdf_url, cache_dir):
    """Download PDF and save to cache directory"""
    try:
        # Create cache directory
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate cache filename based on URL hash
        url_hash = hashlib.md5(pdf_url.encode()).hexdigest()
        cache_file = cache_dir / f"{url_hash}.pdf"
        
        # Check if already cached
        if cache_file.exists():
            print(f"  📥 Using cached PDF: {cache_file.name}")
            return cache_file
        
        # Download PDF
        print(f"  📥 Downloading PDF: {pdf_url}")
        response = requests.get(pdf_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Check if content is actually a PDF
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type and not response.content.startswith(b'%PDF'):
            print(f"  ⚠️  Not a PDF file: {pdf_url}")
            return None
        
        # Save to cache
        with open(cache_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"  ✅ Downloaded: {cache_file.name}")
        return cache_file
        
    except Exception as e:
        print(f"  ❌ Failed to download {pdf_url}: {e}")
        return None

def process_pdf_with_engine(pdf_path, domain, db_path):
    """Process PDF using the existing engine functions"""
    try:
        # Create stable source ID
        file_size = pdf_path.stat().st_size
        file_mtime = int(pdf_path.stat().st_mtime)
        source_id = sha16(f"{pdf_path.name}|{file_size}|{file_mtime}")
        file_hash = sha64(f"{pdf_path.name}|{file_size}|{file_mtime}")
        
        events_count = 0
        seen_events = set()
        
        with sqlite3.connect(db_path) as con:
            # Extract metadata
            with pdfplumber.open(str(pdf_path)) as pdf:
                metadata = extract_metadata(pdf_path, pdf)
                upsert_source(con, source_id, pdf_path.name, metadata)
                doc_id = insert_document(con, source_id, str(pdf_path.resolve()), file_hash)
                
                for page_idx, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue
                    
                    section = guess_section(text.lower())
                    chunk_id = insert_chunk(con, source_id, doc_id, page_idx, section, text)
                    
                    for sent in chunk_sentences(text):
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
        print(f"  ❌ Error processing {pdf_path}: {e}")
        return 0

def main():
    """Main RSS ingestion function"""
    parser = argparse.ArgumentParser(description='RSS Feed Ingestion System')
    parser.add_argument('--feeds-config', type=Path, default=FEEDS_CONFIG,
                       help='Path to RSS feeds configuration JSON file')
    parser.add_argument('--db-path', type=Path, default=DB_PATH,
                       help='Output database path')
    parser.add_argument('--cache-dir', type=Path, default=RSS_CACHE_DIR,
                       help='Cache directory for downloaded PDFs')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be downloaded without actually downloading')
    parser.add_argument('--domain', type=str,
                       help='Override domain for all feeds (for testing)')
    
    args = parser.parse_args()

    try:
        args.feeds_config = validate_file_path(args.feeds_config, must_exist=False)
        args.db_path = validate_database(args.db_path, must_exist=False)
        args.cache_dir = validate_directory(args.cache_dir, must_exist=False)
        if args.domain:
            args.domain = validate_domain_name(args.domain)

        feeds_config = load_feeds_config(args.feeds_config)
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        sys.exit(1)

    # Ensure database and cache directories exist
    args.db_path.parent.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    
    print("📡 RSS FEED INGESTION SYSTEM")
    print("=" * 50)
    print(f"Database: {args.db_path}")
    print(f"Cache: {args.cache_dir}")
    print(f"Feeds config: {args.feeds_config}")
    print()
    
    total_downloaded = 0
    total_processed = 0
    
    # Process each feed
    for feed_config in feeds_config.get('feeds', []):
        if not feed_config.get('enabled', True):
            print(f"⏭️  Skipping disabled feed: {feed_config['name']}")
            continue
        
        feed_url = feed_config['url']
        domain = args.domain if args.domain else feed_config.get('domain', 'methods_tooling')
        
        print(f"📡 Processing feed: {feed_config['name']}")
        print(f"   URL: {feed_url}")
        print(f"   Domain: {domain}")
        
        # Get PDF links from feed
        pdf_links = get_pdf_links_from_feed(feed_url)
        print(f"   Found {len(pdf_links)} PDF links")
        
        if not pdf_links:
            print("   No PDFs found, skipping...")
            continue
        
        # Process each PDF
        feed_downloaded = 0
        feed_processed = 0
        
        for pdf_info in pdf_links:
            pdf_url = pdf_info['url']
            pdf_title = pdf_info['title']
            
            print(f"   📄 {pdf_title}")
            print(f"      URL: {pdf_url}")
            
            if args.dry_run:
                print("      [DRY RUN] Would download and process")
                feed_downloaded += 1
                feed_processed += 1
                continue
            
            # Download PDF
            cache_file = download_pdf(pdf_url, args.cache_dir)
            if not cache_file:
                continue
            
            feed_downloaded += 1
            
            # Process PDF
            events_count = process_pdf_with_engine(cache_file, domain, args.db_path)
            if events_count > 0:
                feed_processed += 1
                print(f"      ✅ Processed: {events_count} events")
            else:
                print("      ⚠️  No events extracted")
        
        total_downloaded += feed_downloaded
        total_processed += feed_processed
        
        print(f"   Summary: {feed_downloaded} downloaded, {feed_processed} processed")
        print()
        
        # Be respectful to servers
        time.sleep(2)
    
    print("=" * 50)
    print("RSS INGESTION COMPLETE")
    print(f"Total downloaded: {total_downloaded}")
    print(f"Total processed: {total_processed}")
    print(f"Database: {args.db_path}")
    
    if args.dry_run:
        print("\n⚠️  This was a dry run - no actual downloads or processing occurred")

if __name__ == "__main__":
    main()