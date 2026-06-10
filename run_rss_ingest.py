#!/usr/bin/env python3
"""Canonical RSS / PDF / abstract ingest engine for AXON."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sqlite3
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import pdfplumber
import requests
from pdfminer.pdfexceptions import PDFNotImplementedError
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException

from utils.abstract_collectors import extract_abstract_text_from_url, find_abstract_links
from utils.domain_router import route_construction_source
from utils.common import sha256_hex
from utils.data_extractors import extract_quantitative_data
from utils.db_init import init_db_schema
from utils.db_utils import (
    connect_with_foreign_keys,
    insert_chunk,
    insert_document,
    insert_event,
    insert_measurement,
    link_event_entity,
    link_event_tag,
    upsert_entity,
    upsert_source,
)
from utils.entities import extract_entities
from utils.event_classification import (
    ConfidenceInput,
    DECISION_PHRASES,
    FAILURE_PHRASES,
    METHOD_TAGS,
    classify_event_type,
    confidence_score,
    detect_decision,
    detect_failure_reason,
    detect_method_tags,
    detect_outcome,
    evidence_strength,
)
from utils.feed_utils import extract_pdf_links, parse_feed
from utils.source_triage import TriagedSource, load_keep_manifest, scan_pdf, write_keep_manifest, write_triage_csv
from utils.site_collectors import _is_safe_url, collect_documents, extract_pdf_links_from_page
from utils.text_utils import chunk_sentences, guess_section, guess_stage


PROJECT_ROOT = Path(__file__).resolve().parent
FEEDS_CONFIG = PROJECT_ROOT / "config" / "feeds.json"
DB_PATH = PROJECT_ROOT / "db" / "rss.sqlite"
DATA_ROOT = PROJECT_ROOT / "data"
RSS_CACHE_DIR = (DATA_ROOT / "cache" / "rss") if DATA_ROOT.exists() else (PROJECT_ROOT / "cache" / "rss")
CONSTRUCTION_TRIAGE_OUTPUT = PROJECT_ROOT / "exports" / "source_triage" / "construction_science_triage.csv"
CONSTRUCTION_KEEP_MANIFEST = PROJECT_ROOT / "exports" / "source_triage" / "construction_science_keep.json"
HTML_DISCOVERY_MIN_INTERVAL_SECONDS = 1.0
_HTML_DISCOVERY_LAST_REQUEST_AT: dict[str, float] = {}
logger = logging.getLogger(__name__)

DOC_LINK_REGEX = re.compile(
    r"(?:https?://)?[^\s<>\"']+\.pdf(?:\?[^\s<>\"']*)?(?:#[^\s<>\"']*)?",
    re.IGNORECASE,
)


def db_operational_error_handler(context_msg):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as oe:
                print(f"❌ DB error during {context_msg}: {oe}")
                if "no such table" in str(oe):
                    print(f"   → Table missing: {context_msg}")
                raise

        return wrapper

    return decorator


@db_operational_error_handler("insert_event")
def _insert_event(*args, **kwargs):
    return insert_event(*args, **kwargs)


@db_operational_error_handler("upsert_entity/link_event_entity")
def _upsert_and_link_entity(con, event_id, entity):
    entity_id = upsert_entity(con, entity["entity_type"], entity["entity_name"], None, None)
    link_event_entity(con, event_id, entity_id, entity.get("role", "unknown"))


@db_operational_error_handler("link_event_tag")
def _link_event_tag(con, event_id, tag):
    link_event_tag(con, event_id, tag)


@db_operational_error_handler("insert_measurement")
def _insert_measurement(con, event_id, measurement):
    insert_measurement(con, event_id, measurement)


def _resolve_pdf_url(base_url: str, url: str) -> str:
    return urljoin(base_url, url) if url else url


def normalize_event_key(event_type, entities, page, snippet):
    entity_str = "|".join(sorted(f"{e.get('entity_type')}:{e.get('entity_name')}" for e in entities))
    return f"{event_type}|{entity_str}|{page}|{sha256_hex(snippet)}"


def has_signal(sentence_l: str) -> bool:
    return (
        any(p in sentence_l for lst in FAILURE_PHRASES.values() for p in lst)
        or any(p in sentence_l for lst in DECISION_PHRASES.values() for p in lst)
        or any(p in sentence_l for lst in METHOD_TAGS.values() for p in lst)
    )


def _triage_construction_pdf(pdf_path: Path, triage_rows: list[TriagedSource]) -> bool:
    try:
        triage = scan_pdf(pdf_path)
    except (PDFSyntaxError, PDFNotImplementedError, PdfminerException, OSError, ValueError, Exception) as exc:
        logger.exception("Failed to triage construction PDF %s", pdf_path)
        triage_rows.append(
            TriagedSource(
                file_path=str(pdf_path),
                title=pdf_path.stem,
                detected_domain="unknown",
                keep_skip_review="review",
                confidence="low",
                construction_signals="",
                contamination_signals="",
                reason=f"failed to scan PDF ({exc.__class__.__name__}) — see logs",
            )
        )
        return False

    triage_rows.append(triage)
    return triage.keep_skip_review == "keep"


def _is_construction_keep_path(pdf_path: Path, keep_paths: set[str]) -> bool:
    return str(pdf_path) in keep_paths


def _process_pdf_urls(
    pdf_urls: list[str],
    domain: str,
    db_path: Path,
    source_title: str,
    *,
    dry_run: bool = False,
    source_triage_rows: list[TriagedSource] | None = None,
    construction_keep_paths: set[str] | None = None,
    construction_keep_manifest_enabled: bool = False,
) -> dict[str, int | bool]:
    pdf_events = 0
    pdf_processed = 0

    for pdf_url in pdf_urls:
        if dry_run:
            pdf_processed += 1
            continue

        if domain == "construction_science":
            route = route_construction_source(title=source_title, text=pdf_url, url=pdf_url)
            if route.decision == "skip":
                print(f"⚠️ Skipping PDF before download ({route.reason})")
                continue

        pdf = download_pdf(pdf_url, RSS_CACHE_DIR)
        if not pdf:
            continue
        if not is_valid_pdf(pdf):
            print("⚠️ Skipping invalid PDF")
            continue

        if domain == "construction_science":
            if construction_keep_manifest_enabled:
                if construction_keep_paths is not None and not _is_construction_keep_path(pdf, construction_keep_paths):
                    print("⚠️ Skipping PDF not listed in keep manifest")
                    continue
            elif source_triage_rows is not None:
                keep_pdf = _triage_construction_pdf(pdf, source_triage_rows)
                if keep_pdf and construction_keep_paths is not None:
                    construction_keep_paths.add(str(pdf))
                if not keep_pdf:
                    print("⚠️ Skipping PDF after source triage")
                    continue

        count = process_pdf(pdf, domain, db_path, source_url=pdf_url, source_title=source_title)
        pdf_processed += 1
        pdf_events += count

    return {
        "pdf_links": len(pdf_urls),
        "pdf_processed": pdf_processed,
        "pdf_events": pdf_events,
    }


def _process_sentence(con, source_id, doc_id, chunk_id, page_number, domain, sent, section, seen):
    s_l = sent.lower()
    if not has_signal(s_l):
        return False

    tags = detect_method_tags(s_l)
    failure = detect_failure_reason(s_l)
    decision = detect_decision(s_l)
    outcome = detect_outcome(s_l)
    stage = guess_stage(s_l)
    event_type = classify_event_type(s_l, tags, failure, decision)
    strength = evidence_strength(s_l)
    entities = extract_entities(sent, domain)
    measurements = extract_quantitative_data(sent)
    conf = confidence_score(
        ConfidenceInput(
            has_entity=bool(entities),
            method_tags=tags,
            failure_reason=failure,
            decision_taken=decision,
            has_measurements=bool(measurements),
            sentence_l=s_l,
        )
    )

    if not (entities or tags or measurements):
        return False

    key = normalize_event_key(event_type, entities, page_number, sent)
    if key in seen:
        return False

    seen.add(key)

    event_id = _insert_event(
        con=con,
        source_id=source_id,
        doc_id=doc_id,
        chunk_id=chunk_id,
        page_number=page_number,
        domain=domain,
        event_type=event_type,
        stage=stage,
        system_context=None,
        application_context=None,
        outcome=outcome,
        failure_reason=failure,
        decision_taken=decision,
        decision_driver=None,
        evidence_snippet=sent,
        evidence_strength_v=strength,
        confidence_v=conf,
    )

    for entity in entities:
        _upsert_and_link_entity(con, event_id, entity)
    for tag in tags:
        _link_event_tag(con, event_id, tag)
    for measurement in measurements:
        _insert_measurement(con, event_id, measurement)

    return True


def load_feeds_config(path: Path) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Malformed JSON in feeds config file {path}: {exc}") from exc


def ensure_db_schema(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_path = PROJECT_ROOT / "schema.sql"
    if not schema_path.exists():
        raise SystemExit(f"Missing schema file: {schema_path}")

    try:
        init_db_schema(db_path)
    except sqlite3.Error as exc:
        raise RuntimeError(f"[ensure_db_schema] Error executing schema script: {exc}") from exc


def get_pdf_links_from_entry(entry: dict[str, Any]) -> list[str]:
    found_urls = extract_pdf_links(entry)

    entry_link = entry.get("link", "")
    if "arxiv.org/abs/" in entry_link:
        arxiv_pdf = entry_link.replace("/abs/", "/pdf/") + ".pdf"
        if arxiv_pdf not in found_urls:
            found_urls.append(arxiv_pdf)

    for link in entry.get("links", []):
        href = link.get("href", "")
        if href and (
            "application/pdf" in link.get("type", "")
            or link.get("title", "").lower() == "pdf"
        ):
            resolved_href = _resolve_pdf_url(entry_link, href)
            if resolved_href and resolved_href not in found_urls:
                found_urls.append(resolved_href)

    pdf_urls = [url for url in found_urls if DOC_LINK_REGEX.search(url)]

    if not pdf_urls and entry_link:
        if not _is_safe_url(entry_link):
            logger.warning("Skipping unsafe HTML discovery URL: %s", entry_link)
            return []
        host = urlparse(entry_link).netloc.lower()
        now = time.monotonic()
        last_request_at = _HTML_DISCOVERY_LAST_REQUEST_AT.get(host)
        if last_request_at is not None:
            elapsed = now - last_request_at
            if elapsed < HTML_DISCOVERY_MIN_INTERVAL_SECONDS:
                time.sleep(HTML_DISCOVERY_MIN_INTERVAL_SECONDS - elapsed)
        try:
            print(f"[DEBUG] Fetching HTML page for PDF discovery: {entry_link}")
            response = requests.get(entry_link, timeout=10)
            _HTML_DISCOVERY_LAST_REQUEST_AT[host] = time.monotonic()
            if response.ok:
                html = response.text
                html_pdfs = DOC_LINK_REGEX.findall(html)
                for url in html_pdfs:
                    resolved_url = _resolve_pdf_url(entry_link, url)
                    if resolved_url not in pdf_urls:
                        pdf_urls.append(resolved_url)
        # HTML fetching and parsing can raise ValueError during parsing or URL handling.
        except (requests.RequestException, ValueError):
            logger.warning(
                "Failed to fetch or parse HTML for PDFs from %s (timeout=%s)",
                entry_link,
                10,
                exc_info=True,
            )
        except Exception:
            logger.exception(
                "Unexpected failure while fetching or parsing HTML for PDFs from %s (timeout=%s)",
                entry_link,
                10,
            )
            return []

    return pdf_urls


def get_pdf_links_from_feed(feed_url: str):
    feed = parse_feed(feed_url)
    if isinstance(feed, dict):
        entries = feed.get("entries", [])
    else:
        entries = getattr(feed, "entries", [])

    pdf_links = []
    seen_pdf_urls = set()

    for entry in entries:
        pdf_urls = get_pdf_links_from_entry(entry)
        for url in pdf_urls:
            if url in seen_pdf_urls:
                continue
            seen_pdf_urls.add(url)
            pdf_links.append({"url": url, "title": entry.get("title", "")})

    return pdf_links


def is_valid_pdf(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(5) == b"%PDF-"
    except Exception:
        return False


def download_pdf(url: str, cache_dir: Path):
    from requests.exceptions import ConnectionError, HTTPError, Timeout

    cache_dir.mkdir(parents=True, exist_ok=True)
    file_path = cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.pdf"
    if file_path.exists():
        return file_path

    headers = {
        "User-Agent": "LabScraper/1.0 (+https://github.com/labscraper/labscraper)",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    }
    max_attempts = 3
    backoff = 1

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, timeout=20, headers=headers)
            response.raise_for_status()
            file_path.write_bytes(response.content)
            return file_path
        except (Timeout, ConnectionError) as exc:
            if attempt == max_attempts:
                logging.error("❌ Download failed after %s attempts: %s", attempt, exc)
                return None
            logging.warning("Network error (attempt %s): %s. Retrying in %ss...", attempt, exc, backoff)
            time.sleep(backoff)
            backoff *= 2
        except HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            try:
                status_code = int(status_code) if status_code is not None else None
            except (TypeError, ValueError):
                status_code = None
            if status_code == 403:
                logging.warning("HTTP 403 for %s; trying range fallback before skipping", url)
                try:
                    ranged_response = requests.get(url, timeout=20, headers={**headers, "Range": "bytes=0-"})
                    ranged_response.raise_for_status()
                    file_path.write_bytes(ranged_response.content)
                    return file_path
                except Exception as fallback_exc:
                    logging.error("❌ HTTP 403 for %s; range fallback failed: %s", url, fallback_exc)
                    return None
            if isinstance(status_code, int) and status_code >= 500 and attempt < max_attempts:
                logging.warning("Server error %s (attempt %s). Retrying in %ss...", status_code, attempt, backoff)
                time.sleep(backoff)
                backoff *= 2
                continue
            logging.error("❌ HTTP error after %s attempts (%s): %s", attempt, status_code, exc)
            return None
        except Exception as exc:
            if attempt == max_attempts:
                logging.error("❌ Unexpected error after %s attempts: %s", attempt, exc)
                return None
            logging.warning("Unexpected error (attempt %s): %s. Retrying in %ss...", attempt, exc, backoff)
            time.sleep(backoff)
            backoff *= 2

    return None


def process_pdf(
    pdf_path: Path,
    domain: str,
    db_path: Path | None = None,
    source_url: str | None = None,
    source_title: str | None = None,
    con: sqlite3.Connection | None = None,
):
    events = 0
    seen = set()

    required_tables = [
        "sources",
        "documents",
        "chunks",
        "entities",
        "research_events",
        "event_entities",
        "tags",
        "event_tags",
        "quantitative_measurements",
    ]

    def check_required_tables(connection):
        cur = connection.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}
        return [table for table in required_tables if table not in tables]

    if con is None:
        if db_path is None:
            raise ValueError("db_path or con must be provided")
        with connect_with_foreign_keys(db_path, timeout=30) as con:
            con.execute("PRAGMA busy_timeout = 30000")
            con.execute("PRAGMA journal_mode = WAL")
            return process_pdf(
                pdf_path,
                domain,
                source_url=source_url,
                source_title=source_title,
                con=con,
            )

    missing_tables = check_required_tables(con)
    if missing_tables:
        print(f"❌ Database schema is missing required tables: {', '.join(missing_tables)}.\n       Please run ensure_db_schema or check your schema migrations.")
        return 0

    try:
        hasher = hashlib.sha256()
        with open(pdf_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()
        initial_source_id = file_hash[:16]
        metadata = {"title": source_title or pdf_path.stem, "url": source_url, "domain": domain}
        if source_url:
            doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9<>%+,]+", source_url, re.I)
            if doi_match:
                metadata["doi"] = doi_match.group(0).rstrip(".,;:")
        source_id = upsert_source(con, initial_source_id, str(pdf_path), metadata)

        with pdfplumber.open(pdf_path) as pdf:
            try:
                doc_id = insert_document(con, source_id, str(pdf_path), file_hash)
                doc_row = con.execute("SELECT source_id FROM documents WHERE doc_id = ? LIMIT 1", (doc_id,)).fetchone()
                canonical_source_id = doc_row[0] if doc_row else source_id
                for page_number, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue

                    section = guess_section(text.lower())
                    chunk_id = insert_chunk(con, doc_id, page_number, section, text)

                    for sent in chunk_sentences(text):
                        if _process_sentence(con, canonical_source_id, doc_id, chunk_id, page_number, domain, sent, section, seen):
                            events += 1
            except sqlite3.OperationalError as exc:
                print(f"❌ DB schema error: {exc}")
                if "no such table" in str(exc):
                    print("   → One or more required tables are missing. Run ensure_db_schema or check your migrations.")
                return 0
    except Exception as exc:
        print(f"❌ Failed to process PDF {pdf_path}: {exc}")
        return 0

    return events


def process_html_document(
    con=None,
    source_url: str | None = None,
    source_title: str | None = None,
    text: str = "",
    domain: str = "",
    db_path: Path | None = None,
    source_type: str = "web_page",
):
    if con is None:
        if db_path is None:
            raise ValueError("db_path or con must be provided")
        with connect_with_foreign_keys(db_path, timeout=30) as con:
            con.execute("PRAGMA busy_timeout = 30000")
            con.execute("PRAGMA journal_mode = WAL")
            return process_html_document(
                con=con,
                source_url=source_url,
                source_title=source_title,
                text=text,
                domain=domain,
                source_type=source_type,
            )

    seen = set()
    return _process_text_document(con, source_url, source_title, text, domain, seen, source_type=source_type)


def _process_text_document(
    con,
    source_url: str,
    source_title: str,
    text: str,
    domain: str,
    seen: set,
    source_type: str = "web_page",
):
    events = 0
    if not text.strip():
        return 0

    file_hash = sha256_hex(text)
    source_id = sha256_hex(source_url or source_title or file_hash)[:16]
    metadata = {
        "title": source_title or source_url,
        "url": source_url,
        "domain": domain,
        "source_type": source_type,
    }

    source_id = upsert_source(con, source_id, source_url or source_title, metadata)
    doc_id = insert_document(con, source_id, source_url or source_title, file_hash)

    section = guess_section(text.lower())
    chunk_id = insert_chunk(con, doc_id, 1, section, text)
    for sent in chunk_sentences(text):
        if _process_sentence(con, source_id, doc_id, chunk_id, 1, domain, sent, section, seen):
            events += 1

    return events


def process_feed_entry(
    entry: dict[str, Any],
    domain: str,
    db_path: Path,
    dry_run: bool = False,
    source_triage_rows: list[TriagedSource] | None = None,
    construction_keep_paths: set[str] | None = None,
    construction_keep_manifest_enabled: bool = False,
) -> dict[str, int | bool]:
    title = entry.get("title", "Unknown")
    entry_text = "\n".join(
        part for part in (
            str(entry.get("summary", "") or "").strip(),
            str(entry.get("description", "") or "").strip(),
            str(entry.get("content", "") or "").strip(),
        )
        if part
    )

    if domain == "construction_science":
        route = route_construction_source(
            title=title,
            text=entry_text,
            url=str(entry.get("link", "") or ""),
        )
        if route.decision == "skip":
            print(f"⚠️ Skipping feed entry before download ({route.reason})")
            return {
                "pdf_links": 0,
                "pdf_processed": 0,
                "pdf_events": 0,
                "abstract_links": 0,
                "abstract_processed": 0,
                "abstract_events": 0,
                "used_abstract_fallback": False,
                "source_routed": "skip",
            }

    pdf_urls = get_pdf_links_from_entry(entry)
    abstract_links = find_abstract_links(entry)
    triage_rows = source_triage_rows

    if pdf_urls:
        pdf_summary = _process_pdf_urls(
            pdf_urls,
            domain,
            db_path,
            title,
            dry_run=dry_run,
            source_triage_rows=triage_rows,
            construction_keep_paths=construction_keep_paths,
            construction_keep_manifest_enabled=construction_keep_manifest_enabled,
        )

        if pdf_summary["pdf_processed"] > 0 or (domain == "construction_science" and (construction_keep_manifest_enabled or triage_rows is not None)):
            return {
                "pdf_links": pdf_summary["pdf_links"],
                "pdf_processed": pdf_summary["pdf_processed"],
                "pdf_events": pdf_summary["pdf_events"],
                "abstract_links": len(abstract_links),
                "abstract_processed": 0,
                "abstract_events": 0,
                "used_abstract_fallback": False,
            }

    abstract_processed = 0
    abstract_events = 0
    for abstract_url in abstract_links:
        try:
            abstract_text = extract_abstract_text_from_url(abstract_url, timeout=30)
        except Exception:
            continue
        if not abstract_text:
            continue

        if dry_run:
            abstract_processed += 1
            break

        count = process_html_document(
            source_url=abstract_url,
            source_title=title,
            text=abstract_text,
            domain=domain,
            db_path=db_path,
            source_type="abstract_fallback",
        )
        abstract_processed += 1
        abstract_events += count
        break

    return {
        "pdf_links": len(pdf_urls),
        "pdf_processed": pdf_summary["pdf_processed"] if pdf_urls else 0,
        "pdf_events": pdf_summary["pdf_events"] if pdf_urls else 0,
        "abstract_links": len(abstract_links),
        "abstract_processed": abstract_processed,
        "abstract_events": abstract_events,
        "used_abstract_fallback": bool(abstract_processed),
        "source_routed": "allow",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--feeds", default=str(FEEDS_CONFIG), help="Path to feeds.json")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to SQLite database")
    args = parser.parse_args()

    feeds_config_path = Path(args.feeds)
    db_path = Path(args.db)
    triage_rows: list[TriagedSource] = []
    triage_enabled = False
    construction_keep_paths = load_keep_manifest(CONSTRUCTION_KEEP_MANIFEST)
    construction_keep_manifest_enabled = CONSTRUCTION_KEEP_MANIFEST.exists()

    ensure_db_schema(db_path)

    try:
        feeds = load_feeds_config(feeds_config_path)
    except FileNotFoundError:
        print(f"❌ Feeds config file not found: {feeds_config_path}")
        sys.exit(1)
    except RuntimeError as exc:
        print(f"❌ Error loading feeds config: {exc}")
        sys.exit(1)

    for feed in feeds.get("feeds", []):
        if not feed.get("enabled", True):
            continue
        source_kind = str(feed.get("source_kind", "rss")).strip().lower()
        if source_kind != "pdf_list" and "url" not in feed:
            print(f"⚠️ Skipping feed entry missing 'url': {feed}")
            continue

        print(f"📡 {feed.get('name') or feed.get('url') or source_kind}")
        domain = feed.get("domain", "methods_tooling")
        if domain == "construction_science":
            triage_enabled = True

        if source_kind == "collector":
            max_pages = int(feed.get("max_pages", 20))
            collector_mode = str(feed.get("collector_mode", "html_archive")).strip().lower()
            print(f"   Collector: {collector_mode}")
            collected_documents = collect_documents(
                feed["url"],
                max_pages=max_pages,
                same_domain_only=bool(feed.get("same_domain_only", True)),
                same_path_prefix=feed.get("same_path_prefix"),
                max_depth=int(feed.get("collector_max_depth", 1)),
                request_timeout=int(feed.get("request_timeout", 20)),
                max_seconds=int(feed.get("collector_timeout_seconds", 60)),
            )
            print(f"[DEBUG] Pages found: {len(collected_documents)}")

            with connect_with_foreign_keys(db_path) as con:
                con.execute("PRAGMA busy_timeout = 30000")
                con.execute("PRAGMA journal_mode = WAL")
                seen_pdf_urls = set()
                for document in collected_documents:
                    print(f"   📄 {document.title}")
                    if args.dry_run:
                        continue

                    if domain == "construction_science":
                        route = route_construction_source(title=document.title, text=document.text, url=document.url)
                        if route.decision == "skip":
                            print(f"   ⚠️ Skipping page before PDF discovery ({route.reason})")
                            continue

                    events = process_html_document(
                        con,
                        document.url,
                        document.title,
                        document.text,
                        domain,
                        source_type=collector_mode,
                    )
                    print(f"   ✅ {events} events")

                    pdf_links = extract_pdf_links_from_page(document.url, timeout=int(feed.get("request_timeout", 20)))
                    for pdf_url in pdf_links:
                        if pdf_url in seen_pdf_urls:
                            continue
                        seen_pdf_urls.add(pdf_url)
                        print(f"      📎 PDF: {pdf_url}")
                        if domain == "construction_science":
                            route = route_construction_source(title=document.title, text=document.text, url=pdf_url)
                            if route.decision == "skip":
                                print(f"⚠️ Skipping PDF before download ({route.reason})")
                                continue
                        pdf = download_pdf(pdf_url, RSS_CACHE_DIR)
                        if not pdf:
                            continue
                        if not is_valid_pdf(pdf):
                            print("⚠️ Skipping invalid PDF")
                            continue
                        if domain == "construction_science":
                            if construction_keep_manifest_enabled:
                                if not _is_construction_keep_path(pdf, construction_keep_paths):
                                    if not _triage_construction_pdf(pdf, triage_rows):
                                        print("⚠️ Skipping PDF not listed in keep manifest")
                                        continue
                                    construction_keep_paths.add(str(pdf))
                            else:
                                if not _triage_construction_pdf(pdf, triage_rows):
                                    print("⚠️ Skipping PDF after source triage")
                                    continue
                                construction_keep_paths.add(str(pdf))
                        count = process_pdf(
                            pdf,
                            domain,
                            db_path,
                            source_url=pdf_url,
                            source_title=document.title,
                            con=con,
                        )
                        print(f"      ✅ {count} events")
                        time.sleep(1)

            continue

        if source_kind == "pdf_list":
            pdf_urls = [str(url).strip() for url in feed.get("pdf_urls", []) if str(url).strip()]
            if not pdf_urls:
                print("⚠️ Skipping pdf_list feed with no pdf_urls")
                continue

            if args.dry_run:
                print(f"   PDF list entries: {len(pdf_urls)}")
                continue

            result = _process_pdf_urls(
                pdf_urls,
                domain,
                db_path,
                feed.get("name", "Unknown"),
            )
            print(f"   📎 PDF links: {result['pdf_links']}")
            if result["pdf_processed"] > 0:
                print(f"   ✅ Processed: {result['pdf_events']} events")
            else:
                print("   ⚠️  No usable PDFs extracted")
            continue

        feed_url = feed["url"]
        parsed_feed = parse_feed(feed_url, timeout=int(feed.get("request_timeout", 20)))
        if isinstance(parsed_feed, dict):
            entries = parsed_feed.get("entries", [])
        else:
            entries = getattr(parsed_feed, "entries", [])
        print(f"[DEBUG] Entries found: {len(entries)}")

        feed_processed = 0
        feed_events = 0
        for entry in entries:
            print(f"   📄 {entry.get('title', 'Unknown')}")
            if args.dry_run:
                continue

            result = process_feed_entry(
                entry,
                domain=domain,
                db_path=db_path,
                dry_run=False,
                source_triage_rows=triage_rows,
                construction_keep_paths=construction_keep_paths,
                construction_keep_manifest_enabled=construction_keep_manifest_enabled,
            )
            if result["pdf_links"]:
                print(f"      📎 PDF links: {result['pdf_links']}")
                if result["pdf_processed"] > 0:
                    print(f"      ✅ Processed: {result['pdf_events']} events")
                else:
                    print("      ⚠️  No usable PDFs extracted")
            elif result["used_abstract_fallback"]:
                print(f"      🔗 Abstract links: {result['abstract_links']}")
                if result["abstract_events"] > 0:
                    print(f"      ✅ Processed: {result['abstract_events']} events")
                else:
                    print("      ⚠️  No events extracted")
            else:
                print("      ⚠️  No PDF or abstract links found")

            feed_processed += result["pdf_processed"] + result["abstract_processed"]
            feed_events += result["pdf_events"] + result["abstract_events"]

        print(f"   Summary: {feed_processed} processed, {feed_events} events extracted")
        print()
        time.sleep(2)

    if triage_enabled:
        write_triage_csv(triage_rows, CONSTRUCTION_TRIAGE_OUTPUT)
        write_keep_manifest(construction_keep_paths, CONSTRUCTION_KEEP_MANIFEST)


if __name__ == "__main__":
    main()
