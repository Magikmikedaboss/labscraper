from __future__ import annotations


from pathlib import Path
import hashlib
import sqlite3
import pdfplumber
from utils.common import sha256_hex
from utils.metadata_utils import extract_metadata
from utils.text_utils import chunk_sentences, guess_stage, guess_section
from utils.data_extractors import extract_quantitative_data
from utils.entities import extract_entities
from utils.event_classification import (
    confidence_score,
    ConfidenceInput,
    detect_method_tags,
    detect_failure_reason,
    detect_decision,
    classify_event_type,
    detect_outcome,
    evidence_strength,
)
from utils.db_utils import (
    upsert_source,
    insert_document,
    insert_chunk,
    insert_event,
    link_event_entity,
    insert_measurement,
    upsert_entity,
)
from utils.db_init import init_db_schema

# Add SEEDS_DIR definition (mirroring run_engine.py)
project_root = Path(__file__).parent.parent.resolve()
SEEDS_DIR = project_root / "input" / "seeds"
if not SEEDS_DIR.exists():
    SEEDS_DIR = project_root / "seeds"

CONSTRUCTION_EVENT_PATTERNS = [
    (
        "moisture_failure",
        ["moisture", "water intrusion", "water leakage", "condensation", "vapor", "wetting"],
        ["failure", "issue", "problem", "damage", "mold", "rot", "leak", "leakage", "poor"],
    ),
    (
        "thermal_performance",
        ["thermal", "temperature", "heat", "cold", "r-value", "u-value", "insulation"],
        ["performance", "resistance", "loss", "transfer", "control", "retention", "insulate"],
    ),
    (
        "insulation_strategy",
        ["insulation", "spray foam", "rigid foam", "batt", "continuous insulation", "air barrier"],
        ["strategy", "assembly", "layer", "retrofit", "detail", "exterior", "interior"],
    ),
    (
        "air_sealing_issue",
        ["air sealing", "air leakage", "airtightness", "infiltration", "exfiltration", "sealant"],
        ["issue", "problem", "leak", "leakage", "failure", "gap", "draft"],
    ),
    (
        "vapor_control",
        ["vapor", "vapour", "vapor diffusion", "vapor retarder", "vapor barrier", "vapor control"],
        ["control", "retarder", "barrier", "diffusion", "perm", "condensation"],
    ),
    (
        "structural_failure",
        ["beam", "column", "slab", "foundation", "wall", "roof", "connection", "panel", "truss", "joist"],
        ["failure", "crack", "cracking", "collapse", "buckling", "deflection", "shear", "settlement", "spalling"],
    ),
    (
        "material_degradation",
        ["corrosion", "weathering", "degradation", "deterioration", "delamination", "fatigue", "freeze-thaw"],
        ["damage", "loss", "degrade", "degraded", "decay", "rot", "mold", "spalling"],
    ),
    (
        "code_or_standard_reference",
        ["iecc", "astm", "asce", "aci", "ul", "iso", "en standard", "code", "standard"],
        ["reference", "compliance", "requirement", "section", "chapter", "table", "clause"],
    ),
    (
        "durability_finding",
        ["durability", "service life", "lifespan", "long-term", "weathering resistance"],
        ["finding", "performance", "resistance", "assessment", "study", "evidence"],
    ),
    (
        "construction_method",
        ["assembly", "retrofit", "installation", "construction", "framing", "enclosure", "detailing", "building"],
        ["method", "approach", "procedure", "system", "detail", "technique"],
    ),
    (
        "climate_load",
        ["climate zone", "climate load", "snow load", "wind load", "rain load", "degree days", "heating degree days", "cooling degree days", "climate normals"],
        ["building", "buildings", "performance", "moisture", "risk", "heating", "cooling", "insulation", "vapor", "vapour", "durability", "material", "wall", "roof", "attic", "foundation", "assembly", "duct", "condensation", "load"],
    ),
]

CLIMATE_ROW_LOCATION_TERMS = {
    "canada",
    "canadian",
    "toronto",
    "vancouver",
    "calgary",
    "edmonton",
    "ottawa",
    "montreal",
    "quebec",
    "halifax",
    "winnipeg",
    "regina",
    "saskatoon",
    "victoria",
    "whitehorse",
    "yellowknife",
    "iqaluit",
    "alberta",
    "british columbia",
    "manitoba",
    "saskatchewan",
    "nova scotia",
    "new brunswick",
    "newfoundland",
    "labrador",
}

CLIMATE_BUILDING_CONTEXT_TERMS = {
    "building",
    "buildings",
    "envelope",
    "performance",
    "moisture",
    "risk",
    "heating",
    "cooling",
    "insulation",
    "vapor",
    "vapour",
    "durability",
    "material",
    "wall",
    "roof",
    "attic",
    "foundation",
    "assembly",
    "duct",
    "condensation",
    "load",
}

CONSTRUCTION_CONTEXT_TERMS = {
    "building",
    "buildings",
    "construction",
    "structural",
    "structure",
    "wall",
    "roof",
    "foundation",
    "slab",
    "beam",
    "column",
    "assembly",
    "envelope",
    "insulation",
    "material",
    "masonry",
    "concrete",
    "steel",
    "frame",
    "facade",
    "cladding",
    "building envelope",
    "roof assembly",
    "wall assembly",
}

CLIMATE_MONTH_TERMS = {
    "jan",
    "january",
    "feb",
    "february",
    "mar",
    "march",
    "apr",
    "april",
    "may",
    "jun",
    "june",
    "jul",
    "july",
    "aug",
    "august",
    "sep",
    "sept",
    "september",
    "oct",
    "october",
    "nov",
    "november",
    "dec",
    "december",
}

ENTITY_NAME_BLACKLIST = {
    "temperature",
    "exposure",
    "pressure",
    "humidity",
    "uv",
    "thermal",
}


def _looks_like_construction_boilerplate(sentence_l: str) -> bool:
    if ("climate normals" in sentence_l or "normales climatiques" in sentence_l) and not _has_climate_building_context(sentence_l):
        return True
    front_matter_terms = {
        "table of contents",
        "contents",
        "list of acronyms",
        "executive summary",
        "disclaimer",
        "authors",
        "acknowledgments",
        "acknowledgements",
        "copyright",
        "all rights reserved",
        "references",
        "bibliography",
        "about this report",
    }
    if any(term in sentence_l for term in front_matter_terms):
        return True
    boilerplate_terms = {"temperature", "humidity", "pressure", "volume", "table", "normals"}
    action_terms = {"load", "performance", "failure", "damage", "strategy", "control", "reference", "issue"}
    if len(boilerplate_terms.intersection(sentence_l.split())) >= 3 and not any(term in sentence_l for term in action_terms):
        return True
    if "climate" in sentence_l and "pressure" in sentence_l and "temperature" in sentence_l and "humidity" in sentence_l:
        return True
    return False


def _has_climate_building_context(sentence_l: str) -> bool:
    return any(term in sentence_l for term in CLIMATE_BUILDING_CONTEXT_TERMS)


def _has_construction_context(sentence_l: str) -> bool:
    return any(term in sentence_l for term in CONSTRUCTION_CONTEXT_TERMS)


def _looks_like_climate_table_row(sentence_l: str, source_title_l: str) -> bool:
    if "climate normals" not in source_title_l and "climate normals" not in sentence_l:
        return False
    if _has_climate_building_context(sentence_l):
        return False

    token_list = [token.strip(".,;:()[]{}") for token in sentence_l.split() if token.strip(".,;:()[]{}")] 
    numeric_tokens = sum(1 for token in token_list if token.replace(".", "", 1).replace("-", "", 1).isdigit())
    month_hits = sum(1 for term in CLIMATE_MONTH_TERMS if term in sentence_l)
    location_hits = sum(1 for term in CLIMATE_ROW_LOCATION_TERMS if term in sentence_l)

    if numeric_tokens >= 3 and len(token_list) <= 18:
        return True
    if month_hits >= 2 and numeric_tokens >= 1:
        return True
    if location_hits >= 1 and numeric_tokens >= 1 and len(token_list) <= 12:
        return True
    if "table" in sentence_l and numeric_tokens >= 2:
        return True
    if "normal" in sentence_l and numeric_tokens >= 2:
        return True
    return False


def _classify_construction_event(sentence_l: str) -> str | None:
    sentence = sentence_l.lower()
    if any(term in sentence for term in ("climate zone", "climate load", "degree days", "heating degree days", "cooling degree days", "climate normals")):
        if _has_climate_building_context(sentence):
            return "climate_load"
    if not _has_construction_context(sentence):
        return None
    for event_type, primary_terms, context_terms in CONSTRUCTION_EVENT_PATTERNS:
        if not any(term in sentence for term in primary_terms):
            continue
        if any(term in sentence for term in context_terms):
            return event_type
    return None


def map_research_domain(meta: dict) -> str:
    """Fallback: Guess research domain from metadata dict."""
    for key in ("domain", "research_domain", "field", "area"):
        if key in meta and meta[key]:
            return str(meta[key])
    return "methods_tooling"


def _sha256_file(path: Path, chunk_size: int = 64 * 1024) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()




def main(input_dir="input/pdfs", db_path="db.sqlite", domain: str | None = None):
    input_dir = Path(input_dir)
    init_db_schema(db_path)
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        pdfs = list(input_dir.rglob("*.pdf"))
        print(f"Found {len(pdfs)} PDFs in {input_dir} (including subfolders)")
        for pdf_path in pdfs:
            meta = {}
            try:
                print(f"\nProcessing: {pdf_path.name}")
                meta = extract_metadata(pdf_path)
                print(f"  Metadata: {meta}")
                # Upsert source and document
                source_id = _sha256_file(pdf_path)
                upsert_source(con, source_id, str(pdf_path), meta)
                file_hash = _sha256_file(pdf_path)
                doc_id = insert_document(con, source_id, str(pdf_path), file_hash)
                source_title_l = str(meta.get("title") or pdf_path.stem).lower()
                resolved_domain = (
                    domain
                    or meta.get("domain")
                    or meta.get("research_domain")
                    or map_research_domain(meta)
                    or "methods_tooling"
                )
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, start=1):
                        text = page.extract_text() or ""
                        section = guess_section(text.lower())
                        chunk_id = insert_chunk(con, doc_id, page_num, section, text)
                        for sent in chunk_sentences(text):
                            sent_l = sent.lower()
                            if resolved_domain == "construction_science" and _looks_like_construction_boilerplate(sent_l):
                                continue
                            if resolved_domain == "construction_science" and _looks_like_climate_table_row(sent_l, source_title_l):
                                continue
                            ents = extract_entities(sent, domain=resolved_domain, SEEDS_DIR=SEEDS_DIR)
                            measurements = extract_quantitative_data(sent)
                            if resolved_domain == "construction_science":
                                event_type = _classify_construction_event(sent_l)
                                if not event_type:
                                    continue
                                if event_type == "climate_load" and not _has_climate_building_context(sent_l):
                                    continue
                                ents = [
                                    ent for ent in ents
                                    if ent.get("entity_name", "").strip().lower() not in ENTITY_NAME_BLACKLIST
                                ]
                                method_tags = detect_method_tags(sent_l)
                                failure_reason = detect_failure_reason(sent_l)
                                decision_taken = detect_decision(sent_l)
                                decision_driver = None
                                if not ents:
                                    continue
                            else:
                                if not ents:
                                    continue
                                method_tags = detect_method_tags(sent_l)
                                failure_reason = detect_failure_reason(sent_l)
                                decision_taken = detect_decision(sent_l)
                                decision_driver = None
                                event_type = classify_event_type(sent_l, method_tags, failure_reason, decision_taken)
                            outcome = detect_outcome(sent_l)
                            evidence_strength_v = evidence_strength(sent_l)
                            stage = guess_stage(sent.lower())
                            confidence = confidence_score(
                                ConfidenceInput(
                                    has_entity=bool(ents),
                                    method_tags=method_tags,
                                    failure_reason=failure_reason,
                                    decision_taken=decision_taken,
                                    has_measurements=bool(measurements),
                                    sentence_l=sent_l
                                )
                            )
                            # Insert event
                            event_id = insert_event(
                                con=con,
                                source_id=source_id,
                                doc_id=doc_id,
                                chunk_id=chunk_id,
                                page_number=page_num,
                                domain=resolved_domain,
                                event_type=event_type,
                                stage=stage,
                                system_context=None,
                                application_context=None,
                                outcome=outcome,
                                failure_reason=failure_reason,
                                decision_taken=decision_taken,
                                decision_driver=decision_driver,
                                evidence_snippet=sent,
                                evidence_strength_v=evidence_strength_v,
                                confidence_v=confidence,
                            )
                            # Persist entities and link to event
                            for ent in ents:
                                entity_id = upsert_entity(
                                    con,
                                    ent.get("entity_type", "unknown"),
                                    ent.get("entity_name", "unknown"),
                                    ent.get("entity_variant"),
                                    ent.get("organism")
                                )
                                # Use ent.get("role") if available, else default to "unknown"
                                link_event_entity(con, event_id, entity_id, ent.get("role", "unknown"))
                            # Persist measurements and link to event
                            for measurement in measurements:
                                try:
                                    insert_measurement(con, event_id, measurement)
                                except ValueError as exc:
                                    print(f"                                Skipping invalid measurement {measurement!r}: {exc}")
                            print(f"    Inserted event: {event_id} (page {page_num})")
                    con.commit()
            except Exception as e:
                print(f"❌ Error processing {pdf_path}: {e}")
                # Optionally record failure status in DB for this source
                try:
                    try:
                        con.rollback()
                        fail_source_id = _sha256_file(pdf_path)
                    except Exception:
                        fail_source_id = sha256_hex(str(pdf_path))
                    existing_source = con.execute(
                        "SELECT title, authors, doi FROM sources WHERE source_id = ? LIMIT 1",
                        (fail_source_id,),
                    ).fetchone()
                    has_valid_metadata = bool(
                        existing_source
                        and any(
                            str(value).strip()
                            for value in (existing_source[0], existing_source[1], existing_source[2])
                            if value is not None
                        )
                    )
                    if not has_valid_metadata:
                        failure_meta = dict(meta) if isinstance(meta, dict) else {}
                        failure_meta.setdefault("title", pdf_path.stem)
                        failure_meta.setdefault("authors", "")
                        failure_meta.setdefault("year", None)
                        failure_meta.setdefault("doi", None)
                        upsert_source(
                            con,
                            fail_source_id,
                            str(pdf_path),
                            failure_meta,
                        )
                except Exception as db_e:
                    print(f"   (DB error while recording failure for {pdf_path}: {db_e})")
                continue


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Modular PDF-to-DB pipeline")
    parser.add_argument('--input-dir', type=str, default="input/pdfs", help="Input directory containing PDFs")
    parser.add_argument('--db-path', '--output-db', dest='db_path', type=str, default="db.sqlite", help="Path to output SQLite database")
    parser.add_argument('--domain', type=str, default=None, help="Explicit research domain override")
    args = parser.parse_args()
    main(input_dir=args.input_dir, db_path=args.db_path, domain=args.domain)