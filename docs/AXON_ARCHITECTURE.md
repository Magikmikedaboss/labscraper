# AXON Architecture

This repository has accumulated several overlapping ingestion paths, domain definitions, and lens systems. The goal of this document is to make the current shape explicit and to identify where complexity can be reduced.

## What AXON Is

AXON is a document intelligence system.

Its primary purpose is to:

1. Discover technical documents
2. Extract structured information
3. Classify findings by domain
4. Store findings in SQLite
5. Generate searchable intelligence and reports

AXON is not:

- a generic web crawler
- a dashboard framework
- a PDF archive
- a collection of unrelated research tools

The architecture should optimize for document intelligence first.

## What each module does

- run_rss_ingest.py: main RSS and PDF ingest runner. It parses feeds, discovers PDF links, downloads PDFs, extracts text, and writes documents, chunks, events, entities, and measurements to SQLite.
- scrape_abstracts.py: alternate ingest path for abstract pages and feed-based sources. It performs sentence extraction and entity/event creation with its own runner logic.
- utils/scrape_pdfs_phase1_full.py: legacy or alternate PDF pipeline with construction-specific heuristics. It has its own boilerplate filters, construction event patterns, and domain handling.
- ui_control_panel.py: desktop UI for selecting domains, lenses, feeds, and output actions.
- export_construction_results.py: exports construction-science rows from the database into CSV files.
- analyze_construction_results.py: prints summary statistics for construction-science output.
- validate_db_results.py, validate_parallel_results.py, quick_validation.py, final_system_verification.py, show_sample_events.py: verification and debugging scripts.
- update_construction_feeds.py: feed maintenance helper for construction-science sources.

- utils/axon_domains.py: canonical domain profile loader and domain profile data model.
- utils/domain_audit.py: audits domain configs, overlays, seed files, and lens mappings.
- utils/domain_enforcement.py: filters entity types by domain and prevents cross-domain contamination.
- utils/feed_utils.py: RSS fetching, parsing, and PDF link extraction from feed entries.
- utils/site_collectors.py: HTML landing-page collector and HTML-based PDF discovery.
- utils/text_utils.py: sentence chunking, stage detection, and section guessing.
- utils/data_extractors.py: numeric and quantitative extraction.
- utils/entities.py: entity extraction and normalization.
- utils/event_classification.py: generic event classification, confidence, strength, and tag logic.
- utils/db_utils.py and utils/db_init.py: SQLite schema creation and persistence helpers.

- lenses/__init__.py: construction lens registry and multi-lens orchestration.
- lenses/construction_common.py: shared construction lens helpers and the LensEvent data model.
- lenses/construction_building_physics_v1.py: detects building-physics signals.
- lenses/construction_climate_v1.py: detects climate and load-related signals.
- lenses/construction_compliance_v1.py: detects code and standards signals.
- lenses/construction_failure_v1.py: detects failure and degradation signals.
- lenses/construction_materials_v1.py: detects material-related signals.

## What each domain does

- construction_science: construction materials, building physics, structural engineering, failure analysis, and code/compliance references. This is the most specialized domain in the repo.
- methods_tooling: methods, assay trends, and reproducibility language.
- biohacking_longevity: observational analysis of longevity, metabolism, cognition, and recovery research.
- neuroscience_cognition: model diversity, method fragmentation, and replication language in neuroscience.
- stem_cells_regen: stem-cell models, differentiation, organoids, engraftment, and translational barriers.
- drug_discovery: targets, compounds, assays, and translational escalation signals.

## What the lenses do

- building_physics: finds sentences about thermal performance, moisture movement, air sealing, and enclosure behavior.
- climate: finds climate-load and climate-normals references, especially when tied to building context.
- compliance: finds code, standard, and requirement language.
- failure: finds failure, degradation, cracking, collapse, and durability signals.
- materials: finds material-specific properties, assemblies, and performance language.
- construction_common.py: shared helpers used by the construction lens suite.

## What is currently active

- Active domain configs: all six files under config/domains are present and loadable.
- Active ingest path: run_rss_ingest.py.
- Active compatibility wrapper: scrape_abstracts.py.
- Legacy or experimental PDF path: utils/scrape_pdfs_phase1_full.py.
- Active construction lens registry: the five construction lens modules listed above are imported and registered in lenses/__init__.py.
- Active construction validation paths: utils/domain_audit.py and utils/domain_enforcement.py are wired to the construction domain rules.

## What is experimental or secondary

- dual_lens blocks in domain configs are secondary overlays, not a single canonical core path.
- construction_science dual-lens scoring is enabled in config, but it is separate from RSS ingest and should be treated as a specialized analysis mode.
- biohacking_longevity also carries dual_lens metadata, which adds another layer of policy complexity.
- utils/scrape_pdfs_phase1_full.py contains a second construction-specific event pipeline and is best treated as legacy or experimental until it is clearly the one true PDF path.

## What should be kept, merged, demoted, or simplified

### Keep

- Keep utils/axon_domains.py as the canonical domain profile loader.
- Keep config/domains as the single editable source for domain definitions.
- Keep one construction lens package, but only if it remains a coherent, bounded surface.
- Keep the domain audit and enforcement utilities, because they are the right place to catch drift.

### Merge

- Merge run_rss_ingest.py and utils/scrape_pdfs_phase1_full.py around one canonical PDF ingest engine. Today they both decide how PDFs become events, which is redundant.
- Merge the five construction lens modules conceptually behind one higher-level construction detector, with one public interface and five internal modules unless there is a clear reason to preserve separate rule files.
- Merge the RSS feed parser and site collector entry points into a smaller ingestion API so the feed path and HTML discovery path share the same fetch and filtering rules.

### Retire or make thin wrappers

- scrape_abstracts.py is already a thin wrapper / compatibility path.
- utils/scrape_pdfs_phase1_full.py should stay legacy until it is either merged into the canonical engine or archived.
- Demote one-off validation and export scripts out of the normal workflow when they are not part of the core run loop. Keep them archived for debugging and recovery.
- Demote dual_lens to an optional reporting/export mode unless a single canonical use case is documented.

### Simplify next

- Tighten the construction signal filters before adding more lenses. The low-signal PDFs are usually low-value inputs, not evidence that another lens is missing.
- Reduce domain-specific branching in PDF ingestion. The more the engine special-cases domain names, the harder it is to reason about.
- Prefer configuration over new modules. New behavior should first be expressed in the domain JSON or existing rule tables.

### Recommended order

1. Pick the one canonical PDF ingest engine.
2. Remove duplicate construction-specific PDF logic from the alternate path.
3. Consolidate construction lens behavior into one interface.
4. Keep only the domain and validation layers that enforce that contract.
5. Demote scripts that are only useful for manual inspection, but keep them available as archived/debug tools.

## Canonical direction

AXON should use this flow:

Source discovery
→ document download
→ canonical PDF/text ingest engine
→ domain enforcement
→ construction/insurance event detection
→ SQLite
→ exports/dashboard

Any script that does not fit this flow should become one of these:

- a wrapper around the canonical engine
- a debugging tool
- an archived legacy script

## Current Priority

The current priority is not adding new domains.

The current priority is:

- selecting one ingest engine
- improving extraction quality
- reducing duplicate pipelines
- improving construction and insurance intelligence

New domains should only be added after the core pipeline is simplified.

## Bottom line

The repository is already multi-domain and multi-lens, but the RSS ingest path is not actually using the construction lens registry. The most productive simplification is to pick one ingest engine, one domain source of truth, and one construction lens implementation instead of growing the parallel stacks.