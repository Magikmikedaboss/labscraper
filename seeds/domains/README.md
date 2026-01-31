# Axon Labs Domain Profiles
# IMPORTANT: Domains vs Entities

**Domains** are the organizing axes for research intelligence (e.g., methods_tooling, drug_discovery, neuroscience_cognition, etc.).

**Entities** (such as peptides, proteins, cell types) are extracted and tracked within each domain, but are not valid as top-level domains themselves.

**Do not use entity names (like 'peptide') as domains.**

If your research is about construction science, use the `construction_science` domain. Peptides and other biological entities will still be extracted as entities within that domain.

If your research is about drug discovery, use the `drug_discovery` domain. Peptides will be treated as primary entities, but the domain remains `drug_discovery`.

This distinction keeps your taxonomy clean and prevents confusion between research axes and extracted entities.


## Ontology Guidance: Domain → Lens → Entities → Evidence

- **Domain**: The research axis (e.g., methods_tooling, drug_discovery)
- **Lens**: The observational or scoring perspective (e.g., dual-lens overlays)
- **Entities**: Extracted items of interest (e.g., peptides, models, assays)
- **Evidence**: The supporting text, data, or patterns

This structure ensures clarity and extensibility for all research intelligence workflows.

Domain profiles provide **observational lenses** for research intelligence without rewriting the core engine.

## What Are Domain Profiles?

Domain profiles are JSON configuration files that:
- Define domain-specific **language guardrails** (observational only, no medical claims)
- Apply **soft emphasis** to pattern scores (lens, not rewrite)
- Specify **preferred entity types** for each domain
- Filter out **excluded terms** (e.g., "supplement", "coupon", "miracle")
- Maintain **version history** for reproducibility

## Available Domains

### 6. Construction Science (`construction_science.json`)
- **Focus**: Materials, structural health monitoring, sustainability, building codes, and construction methods
- **Emphasis**: Convergence/Escalation (1.15x/1.10x)
- **Preferred Types**: material, sensor, method, code_standard, property
- **Exclusions**: vendor/promotional language, product claims, marketing
- **Language**: Neutral scientific phrasing, evidence-based, technical descriptions
- **Forbidden**: Absolute claims ("guaranteed", "best", "miracle"), vendor-specific endorsements

### 1. Biohacking & Longevity (`biohacking_longevity.json`)
- **Focus**: Human performance, longevity, metabolism, cognition, recovery
- **Emphasis**: Escalation (1.20x), Convergence (1.05x)
- **Preferred Types**: biomarker, pathway, assay, model, indication
- **Exclusions**: supplement, vendor, affiliate, coupon, proprietary blend, testosterone booster
- **Language**: "research momentum", "observed patterns", "appears to", "associated with"
- **Forbidden**: "works", "effective", "proven", "safe", "recommended", "treats", "cures"

### 2. Stem Cells & Regenerative Biology (`stem_cells_regen.json`)
- **Focus**: MSC/iPSC models, differentiation, organoids, engraftment, translational barriers
- **Emphasis**: Escalation (1.25x), Stagnation (1.10x)
- **Preferred Types**: model, pathway, assay, indication
- **Exclusions**: clinic, miracle, guaranteed, stem cell spa
- **Language**: "research momentum", "protocol diversity", "translational friction", "reported limitations"
- **Forbidden**: "cure", "reverses aging", "guaranteed", "FDA approved (unless cited)"

### 3. Neuroscience & Cognition (`neuroscience_cognition.json`)
- **Focus**: Model diversity, method fragmentation, translational gaps, replication language
- **Emphasis**: Fragmentation (1.15x), Escalation (1.10x), Stagnation (1.05x)
- **Preferred Types**: model, assay, pathway, indication
- **Exclusions**: nootropics store, supplement stack, coupon
- **Language**: "model divergence", "method diversity", "replication language", "reported outcomes"
- **Forbidden**: "boosts IQ", "fixes depression", "cures Alzheimer's"

### 4. Drug Discovery (`drug_discovery.json`)
- **Focus**: Targets, compounds, assays, escalation signals, translational development
- **Emphasis**: Escalation (1.20x), Convergence (1.10x)
- **Preferred Types**: target, compound, assay, pathway, indication
- **Exclusions**: coupon, buy now
- **Language**: "research momentum", "validation effort", "appears to"
- **Forbidden**: "approved", "clinically proven" (unless citing specific trial)

### 5. Methods & Tooling (`methods_tooling.json`)
- **Focus**: Method convergence, assay trends, reproducibility language
- **Emphasis**: Convergence (1.20x)
- **Preferred Types**: assay, pathway, model
- **Exclusions**: supplement, clinic
- **Language**: "method convergence", "assay trends", "appears to"
- **Forbidden**: "best method", "guaranteed"

## Domain Profile Structure

```json
{
  "id": "domain_id",
  "name": "Human-Readable Name",
  "description": "Domain description and disclaimers",
  "claims_mode": "observational_only",
  "domain_profile_version": "v1",
  "seed_overlays": {
    "include_files": ["assays.json", "pathways.json"],
    "prefer_types": ["assay", "pathway", "model"]
  },
  "exclusions": {
    "terms": ["supplement", "coupon", "miracle"],
    "doc_kinds": ["ecommerce", "marketing"]
  },
  "pattern_emphasis": {
    "convergence": 1.0,
    "escalation": 1.2,
    "fragmentation": 1.0,
    "stagnation": 1.0,
    "abandonment": 0.95
  },
  "language": {
    "allowed": ["research momentum", "appears to", "reported outcomes"],
    "forbidden": ["works", "proven", "cures"]
  }
}
```

## How to Use

### Python (Engine)

```python
from axon_domains import load_domain_profile, load_all_domains

# Load a specific domain
domain = load_domain_profile("seeds/domains/stem_cells_regen.json")

# Filter out excluded text
if domain.is_excluded_text(full_text):
    return  # skip this document

# Apply soft emphasis to pattern scores
pattern_score = domain.emphasize_pattern(pattern_type, pattern_score)

# Check for forbidden language
if domain.is_forbidden_language(interpretation_text):
    # Rewrite or flag for review
    pass

# Get preferred entity types
preferred_types = domain.get_preferred_entity_types()
```

### TypeScript (Next.js)

```typescript
import { DOMAINS, getDomain } from '@/lib/domains';

// Get domain
const domain = getDomain('stem_cells_regen');

// Use in UI
<h1>{domain.name}</h1>
<p>{domain.description}</p>

// Filter data
const filteredEvents = events.filter(e => 
  e.domain_id === 'stem_cells_regen'
);
```

## Pattern Emphasis Explained

Pattern emphasis values are **soft multipliers** (not rewrites):
- **1.20x** = 20% boost (domain strongly values this pattern)
- **1.00x** = No change (neutral)
- **0.90x** = 10% reduction (domain de-emphasizes this pattern)

Example:
- Base score: 50
- Escalation emphasis: 1.20x
- Domain-adjusted score: 50 × 1.20 = 60

This is a **lens**, not a rewrite. The base score remains unchanged in the database.

## Adding New Domains

1. Copy an existing domain JSON file
2. Update all fields (id, name, description, etc.)
3. Adjust pattern emphasis for domain focus
4. Add domain-specific exclusions
5. Define allowed/forbidden language
6. Test with `python axon_domains.py`
7. Add to TypeScript `DOMAINS` registry (for Next.js)

## Versioning

Always include `domain_profile_version` in your JSON:
```json
{
  "domain_profile_version": "v1"
}
```

When making breaking changes:
- Increment version (v1 → v2)
- Keep old version files for reproducibility
- Document changes in this README

## Best Practices

1. **Observational Only**: All domains use `"claims_mode": "observational_only"`
2. **No Medical Claims**: Forbidden language prevents medical claims
3. **Soft Emphasis**: Pattern multipliers are gentle (0.9-1.25x range)
4. **Exclusion Precision**: Use word boundaries for single words, substring for phrases
5. **Version Everything**: Track domain profile versions for reproducibility
6. **Test Exclusions**: Run `python axon_domains.py` to test exclusion logic

## Integration Points

### Pattern Intelligence Export
- Add `domain_id`, `domain_name`, `pattern_score_domain` columns
- Apply domain emphasis to health scores
- Filter forbidden language from interpretations

### Next.js Dashboard
- Domain switcher component
- Domain-specific copy and disclaimers
- Filter events/entities by domain
- Display domain-adjusted scores

### Future Enhancements
- Domain-specific seed overlays (load different seed files per domain)
- Multi-domain support (one entity, multiple domain lenses)
- Domain-specific confidence thresholds
- Domain-specific outcome signal weights

## Questions?

See `axon_domains.py` for implementation details and examples.
