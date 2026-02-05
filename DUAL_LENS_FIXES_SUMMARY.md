# Dual-Lens Export Fixes Summary

## Problem Analysis

The dual-lens export was producing identical results across all overlays because:

1. **Overlay scoring was working correctly** - The `overlay_scorer.py` had proper boost/demote logic
2. **Entity filtering issues** - Junk entities like "]" and "indirect (peptide)" were appearing
3. **Domain contamination** - Bio terms (peptide/compound) were leaking into construction domain
4. **Climate terms not showing up** - Climate exposures were being buried by materials

## Root Causes Identified

1. **Entity filtering missing**: No validation to remove punctuation-only entities
2. **Domain-specific filtering**: No mechanism to suppress bio entity types in construction domain
3. **Climate terms present but buried**: Materials had higher base counts, climate terms needed stronger promotion
4. **Co-occurrence promotion missing**: Climate exposures needed to be boosted when paired with materials

## Fixes Implemented

### 1. Enhanced Entity Filtering (`utils/enhanced_entity_extractor.py`)

**Added domain-specific entity validation:**
- Filter out junk entities (brackets, punctuation, numbers, short abbreviations)
- Filter out biomedical entity types from construction domain
- Filter out construction terms from biomedical domains
- Added `_is_valid_entity_for_domain()` method with comprehensive pattern matching

**Key improvements:**
```python
def _is_valid_entity_for_domain(self, entity_name: str, entity_type: str) -> bool:
    # Filter out junk entities
    junk_patterns = [
        r'^[\[\]{}()]$',  # Single brackets
        r'^[^\w\s]+$',    # Only punctuation
        r'^\d+$',         # Only numbers
        r'^[a-z]{1,2}$',  # Very short lowercase (likely abbreviations)
        r'^indirect.*$',  # Indirect references
        r'^unknown.*$',   # Unknown entities
        r'^unspecified.*$', # Unspecified entities
    ]
    
    # Domain-specific filtering
    if self.domain == "construction_science":
        # Filter out biomedical entity types
        bio_entity_types = ['compound', 'target', 'pathway', 'indication', 'assay', 'peptide']
        if entity_type in bio_entity_types:
            return False
        
        # Filter out biomedical terms
        bio_terms = ['peptide', 'compound', 'target', 'pathway', 'indication', 'assay', 'protein', 'gene']
        if any(term in entity_lower for term in bio_terms):
            return False
```

### 2. Enhanced Climate Overlay Configuration (`seeds/overlays/climate_resilience_v1.json`)

**Strengthened climate term promotion:**
- Increased boost weights for core climate terms from 2.0 to 3.0
- Increased boost weights for secondary terms from 1.5 to 2.0
- Added comprehensive list of climate-related terms (100+ terms)
- Enhanced priority entities for climate resilience

**Key improvements:**
```json
{
  "boost_terms": {
    "freeze-thaw": 3.0,        // Increased from 2.0
    "freeze thaw": 3.0,        // Increased from 2.0
    "frost action": 3.0,       // Increased from 2.0
    "chloride ingress": 3.0,   // Increased from 2.0
    "thermal cycling": 2.0,    // Increased from 1.5
    "temperature cycling": 2.0, // Increased from 1.5
    // ... 100+ additional climate terms added
  }
}
```

### 3. Co-occurrence Scoring Logic (`utils/overlay_scorer.py`)

**Added climate-material interaction detection:**
- Detects when climate terms appear with material terms
- Applies bonus scoring for climate-material co-occurrence
- Promotes research signals that study climate effects on materials

**Key improvements:**
```python
def _calculate_co_occurrence_bonus(self, text_lower: str, overlay: Dict) -> float:
    """Calculate co-occurrence bonus for climate resilience overlay"""
    bonus = 0.0
    
    # Climate terms that should be boosted when with materials
    climate_terms = [
        'freeze-thaw', 'freeze thaw', 'frost', 'chloride', 'salt', 'carbonation',
        'thermal', 'temperature', 'humidity', 'UV', 'solar', 'wind', 'seismic',
        'flood', 'arctic', 'tropical', 'climate', 'resilience', 'adaptation'
    ]
    
    # Material terms that indicate construction context
    material_terms = [
        'concrete', 'steel', 'wood', 'glass', 'brick', 'masonry', 'foundation',
        'beam', 'column', 'wall', 'roof', 'floor', 'insulation', 'coating'
    ]
    
    # Check for co-occurrence
    climate_found = any(term in text_lower for term in climate_terms)
    material_found = any(term in text_lower for term in material_terms)
    
    if climate_found and material_found:
        # Apply bonus for climate-material co-occurrence
        bonus = 1.5
    
    return bonus
```

## Expected Outcomes

With these fixes, the dual-lens export should now:

1. **Remove junk entities** - No more "]" or "indirect (peptide)" entities
2. **Prevent domain contamination** - Bio terms won't leak into construction domain
3. **Promote climate terms** - Climate exposures will have stronger scores
4. **Highlight climate-material interactions** - Research studying climate effects on materials will be prioritized
5. **Produce distinct overlay results** - Each overlay will have unique entity rankings

## Files Modified

1. `utils/enhanced_entity_extractor.py` - Added domain-specific entity filtering
2. `seeds/overlays/climate_resilience_v1.json` - Enhanced climate term promotion
3. `utils/overlay_scorer.py` - Added co-occurrence scoring logic

## Testing

The fixes have been implemented and are ready for testing. To verify the improvements:

1. Run the dual-lens export: `python export_dual_lens.py <database> <domain>`
2. Check the generated CSV files for distinct entity rankings across overlays
3. Verify that junk entities are filtered out
4. Confirm that climate terms appear with higher scores in the climate resilience overlay
5. Look for climate-material co-occurrence bonuses in the scoring

## Next Steps

1. Test the fixes with actual construction science data
2. Verify that the dual-lens export produces distinct results across overlays
3. Fine-tune boost weights if needed based on test results
4. Consider adding similar co-occurrence logic for other domain combinations

The implementation addresses all the identified root causes and should resolve the issue of identical results across overlays.