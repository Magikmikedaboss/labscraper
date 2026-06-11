# AXON Future Work

This file is the current working roadmap for AXON.

The architecture summary lives in [AXON_ARCHITECTURE.md](AXON_ARCHITECTURE.md).

## Current Goal

Reduce complexity before adding anything new.

The current priority is:

- selecting one canonical ingest engine
- improving extraction quality
- reducing duplicate pipelines
- tightening construction signal quality

## Phase 1: Pick the Canonical Ingest Engine

Status: complete.

Decision made:

- [run_rss_ingest.py](run_rss_ingest.py) is the canonical ingest engine.
- [scrape_abstracts.py](scrape_abstracts.py) is a compatibility wrapper for older workflows.
- [utils/scrape_pdfs_phase1_full.py](utils/scrape_pdfs_phase1_full.py) is legacy or experimental until it is formally retired or folded into the canonical path.

What changed:

- one clear document-to-event pipeline now owns the normal RSS and PDF flow
- abstract fallback lives inside the canonical engine instead of a duplicate stack
- the wrapper still exists, but only as a thin entry point for older commands

Remaining cleanup:

- decide whether the legacy PDF path should be archived, merged, or removed later
- keep the canonical ingest rules in one place as Phase 2 work uncovers quality issues

## Phase 2: Validate Construction Science Output

Use the existing construction-science corpus to confirm quality before expanding scope.

Initial finding from the first pass:

- the current construction-science database contains mixed-source contamination, including stem-cell and biomedical material
- review should start at the source level before trusting event labels
- construction-oriented PDFs exist, but the corpus is not yet clean enough to treat every event as construction-science signal

First step:

- build a scan-and-skip source triage filter before extraction
- do not delete, move, or modify any PDFs
- scan title, metadata, first pages, and a text sample for each PDF
- classify each file as `keep`, `skip`, or `review`
- write a triage CSV to `exports/source_triage/construction_science_triage.csv`
- process only files marked `keep`

Construction keep signals:

- building envelope
- moisture
- vapor
- insulation
- thermal performance
- roof
- wall assembly
- attic
- crawlspace
- foundation
- materials
- structural
- code
- ASHRAE
- ASTM
- FEMA
- DOE
- NIST
- Building Science Corporation

Construction skip signals:

- peptide
- stem cell
- assay
- protein
- receptor
- kinase
- mouse model
- serum
- plasma
- clinical trial
- drug discovery

Tasks:

- sample events by event type after triage
- review evidence snippets manually
- check whether event labels match the source text
- identify false positives and boilerplate leakage
- keep a decision list of skipped files for review

Success criteria:

- event types are understandable by inspection
- low-signal PDFs are separated from useful PDFs
- construction filters are stable enough to trust

## Phase 3: Keep the Domain Surface Small

Do not add new domains until the pipeline is simpler.

Deferred domains:

- insurance_property_claims
- forensic_engineering
- weather_risk
- any new exploratory domain

Only revisit after the core ingest path is stable.

## Phase 4: Simplify the Lens Architecture

Keep the construction lens suite conceptually unified.

Tasks:

- keep one public construction lens interface
- keep the internal building physics, climate, compliance, failure, and materials modules organized behind it
- avoid adding new lens modules unless they replace something

## Phase 5: Add Reporting Only After the Core Is Stable

Once ingestion and validation are stable, build a small explorer for existing data.

Initial reporting scope:

- sources
- events
- entities
- domains
- search

## Do Not Do Yet

- do not add new feeds
- do not add new lenses
- do not add new domains
- do not build a dashboard before the ingest path is stable

## Working Rule

If a change does not make the canonical ingest path clearer, simpler, or more trustworthy, it is probably not the next task.