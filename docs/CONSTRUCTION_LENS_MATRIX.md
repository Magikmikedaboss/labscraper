# Construction Lens Matrix

This matrix summarizes the current construction-science lens stack.

| Lens | Detects | Event Type | Entity Types | Best Questions It Answers | Scoring Fields | Example Sentence |
| --- | --- | --- | --- | --- | --- | --- |
| Building Physics | Heat, air, moisture, comfort, envelope performance, thermal metrics | `building_physics_performance` | `building_component`, `physics_metric` | Is the building envelope performing better or worse? Are thermal or moisture conditions improving? | `event_type`, `outcome`, `raw_outcome`, `confidence`, `context_strength`, `source_weight`, `tags`, `lens` | "The wall assembly reduced heat loss and improved airtightness, lowering the U-value." |
| Climate | Flood, wind, wildfire, freeze-thaw, humidity, resilience, adaptation | `climate_resilience` | `hazard`, `resilience_term`, `material`, `system` | What climate hazards are mentioned? Is the structure being framed as resilient, exposed, or at risk? | `event_type`, `outcome`, `raw_outcome`, `confidence`, `context_strength`, `source_weight`, `tags`, `lens` | "Concrete facades improved resilience against freeze-thaw cycles and wind-driven rain." |
| Compliance | Codes, standards, pass/fail language, compliance claims | `code_compliance` | `code_standard` | Does the text describe code compliance, a pass/fail result, or a standards reference? | `event_type`, `outcome`, `raw_outcome`, `confidence`, `context_strength`, `source_weight`, `tags`, `lens` | "The assembly complies with ASTM E84 and meets IECC requirements." |
| Failure | Cracking, corrosion, collapse, water intrusion, causal failure language | `failure_analysis` | `failure_mode`, `failure_driver` | What failed, why did it fail, and what mechanisms or drivers are named? | `event_type`, `outcome`, `raw_outcome`, `confidence`, `context_strength`, `source_weight`, `tags`, `lens` | "The slab exhibited cracking due to chloride ingress and corrosion of the reinforcement." |
| Materials | Concrete, steel, timber, insulation, durability, strength, material properties | `material_performance` | `material`, `property` | Which material or property is being measured, and is the result improved or degraded? | `event_type`, `outcome`, `raw_outcome`, `confidence`, `context_strength`, `source_weight`, `tags`, `lens` | "High-strength concrete showed increased compressive strength and better durability after curing." |

## Shared Scoring Fields

All construction lenses feed the same downstream event structure:

- `event_type`: the normalized lens event class
- `outcome`: normalized bucket such as positive, negative, neutral, or failed
- `raw_outcome`: the lens-specific source outcome before normalization
- `confidence`: low, med, or high
- `context_strength`: weak, moderate, or strong
- `source_weight`: source trust weight assigned by source type
- `tags`: lens-specific indicators used for sorting and reporting
- `lens`: the originating lens name

## Notes

- The construction stack is now isolated from `biohacking_longevity`.
- The construction domain uses the five lenses above only.
- These lenses are designed to surface construction-science signals, not biomedical scoring.