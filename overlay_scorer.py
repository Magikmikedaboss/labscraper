"""
Phase 2: Overlay Scoring System
Applies overlay-specific scoring to extracted events and entities
Includes model weighting for translational relevance
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class OverlayScorer:
    """Applies overlay scoring to events and entities with model weighting"""
    
    def __init__(self, domain_config: Dict[str, Any]):
        """
        Initialize overlay scorer with domain configuration
        
        Args:
            domain_config: Domain configuration dict with overlays list
        """
        self.domain_config = domain_config
        self.overlays = {}
        self.dual_lens = domain_config.get('dual_lens', False)
        self.model_weights = {}
        
        # Load model weights
        self.load_model_weights()
        
        # Load all overlays specified in domain config
        if 'overlays' in domain_config:
            for overlay_id in domain_config['overlays']:
                self.load_overlay(overlay_id)
    
    def load_model_weights(self):
        """Load model weights from config file"""
        weights_path = Path("config/model_weights.json")
        
        if not weights_path.exists():
            print(f"⚠️  Model weights not found: {weights_path}, using defaults")
            return
        
        with open(weights_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.model_weights = config.get('weights', {})
        
        print(f"✅ Loaded {len(self.model_weights)} model weights")
    
    def load_overlay(self, overlay_id: str):
        """Load overlay configuration from JSON file"""
        overlay_path = Path("seeds/overlays") / f"{overlay_id}.json"
        
        if not overlay_path.exists():
            print(f"⚠️  Overlay not found: {overlay_path}")
            return
        
        with open(overlay_path, 'r', encoding='utf-8') as f:
            self.overlays[overlay_id] = json.load(f)
        
        print(f"✅ Loaded overlay: {overlay_id}")
    
    def apply_event_scores(self, event: Dict[str, Any]) -> Dict[str, float]:
        """
        Apply overlay scoring to a single event
        
        Args:
            event: Event dict with 'evidence_snippet' or 'sentence' field
        
        Returns:
            Dict mapping overlay_id to score
        """
        scores = {}
        
        # Get text to analyze
        text = event.get('evidence_snippet') or event.get('sentence', '')
        text_lower = text.lower()
        
        for overlay_id, overlay in self.overlays.items():
            score = 0
            
            # Apply boost terms
            boost_terms = overlay.get('boost_terms', {})
            for term, weight in boost_terms.items():
                if term.lower() in text_lower:
                    score += weight
            
            # Apply demote terms (weights are negative)
            demote_terms = overlay.get('demote_terms', {})
            for term, weight in demote_terms.items():
                if term.lower() in text_lower:
                    score += weight  # weight is already negative
            
            scores[overlay_id] = score

        # Efficacy demotion for science overlay
        assay_keywords = ["lc-ms", "elisa", "western blot", "rna-seq", "flow cytometry", "mass spectrometry", "hplc", "nmr", "fluorescence", "spectrometry"]
        for overlay_id in self.overlays:
            if overlay_id == "science_research_v1":
                if ("efficacy" in text_lower or "effective" in text_lower) and not any(k in text_lower for k in assay_keywords):
                    scores[overlay_id] -= 1.0

        return scores
    
    def apply_entity_priority(self, entity_type: str, overlay_id: str) -> float:
        """
        Get priority weight for entity type in specific overlay
        
        Args:
            entity_type: Type of entity (compound, target, pathway, etc.)
            overlay_id: ID of overlay to check
        
        Returns:
            Priority multiplier (default 1.0)
        """
        if overlay_id not in self.overlays:
            return 1.0
        
        overlay = self.overlays[overlay_id]
        priority_entities = overlay.get('priority_entities', {})
        
        return priority_entities.get(entity_type, 1.0)
    
    def model_factor(self, models: List[str]) -> float:
        """
        Calculate model weight factor from list of models
        
        Args:
            models: List of model names mentioned in entity context
        
        Returns:
            Average model weight, capped at 2.0 to prevent runaway scores
        """
        if not models:
            return 1.0
        
        weights = []
        for model in models:
            model_lower = model.lower().strip()
            weight = self.model_weights.get(model_lower, 1.0)
            weights.append(weight)
        
        # Average and cap to prevent explosion
        avg_weight = sum(weights) / len(weights)
        return min(2.0, avg_weight)
    
    def calculate_entity_score(self, entity: Dict[str, Any], 
                              event_scores: List[float],
                              overlay_id: str,
                              entity_models: List[str] = None) -> float:
        """
        Calculate final entity score for specific overlay with model weighting
        
        Scoring formula:
        final = base_count * priority_weight * model_factor + capped_language_score + lens_adjustment
        
        Args:
            entity: Entity dict with entity_type and base_count
            event_scores: List of event scores where this entity appeared
            overlay_id: ID of overlay to score for
            entity_models: List of models associated with this entity (optional)
        
        Returns:
            Final weighted score
        """
        # Step 1: Base score from event count
        base_score = entity.get('event_count', len(event_scores))
        
        # Step 2: Apply entity-type priority weight for this lens
        entity_type = entity.get('entity_type', 'unknown')
        priority_weight = self.apply_entity_priority(entity_type, overlay_id)
        
        # Step 3: Apply model weight factor (translational relevance)
        model_weight = self.model_factor(entity_models or [])
        
        # Step 4: Calculate language score from boost/demote terms
        # Cap to prevent single high-boost terms from dominating
        avg_event_score = sum(event_scores) / len(event_scores) if event_scores else 0
        capped_language_score = min(avg_event_score, base_score * 0.5)  # Cap at 50% of base
        
        # Step 5: Combine into final score
        final_score = (base_score * priority_weight * model_weight) + capped_language_score
        
        # Step 6: Apply lens-specific post-adjustments
        # 🎯 Infrastructure dampening (biohacking_curiosity lens only)
        # Prevents generic models/context from crowding out compounds/indications
        INFRA_MODELS = {"human", "humans", "serum", "plasma", "blood", "tissue", "in vivo", "in vitro"}

        if overlay_id == "biohacking_curiosity_v1":
            entity_name = entity.get('entity_name', '').lower()

            # Dampen infrastructure (extended list)
            INFRA_EXTENDED = INFRA_MODELS | {"tissue", "blood"}
            if entity_name in INFRA_EXTENDED:
                final_score *= 0.5  # Stronger dampening for extended infra list
        
        return final_score
    
    def bucket_score(self, score: float, max_score: float = 100) -> str:
        """
        Convert numeric score to bucket label
        
        Args:
            score: Numeric score
            max_score: Maximum possible score for normalization
        
        Returns:
            Bucket label (strong, promising, exploratory, stalled, deprioritized)
        """
        # Normalize to 0-100 scale
        normalized = (score / max_score * 100) if max_score > 0 else 0
        
        if normalized >= 80:
            return "strong"
        elif normalized >= 60:
            return "promising"
        elif normalized >= 40:
            return "exploratory"
        elif normalized >= 20:
            return "stalled"
        else:
            return "deprioritized"
    
    def get_overlay_ids(self) -> List[str]:
        """Get list of loaded overlay IDs"""
        return list(self.overlays.keys())
    
    def is_dual_lens(self) -> bool:
        """Check if dual-lens mode is enabled"""
        return self.dual_lens


def load_domain_config(domain_id: str) -> Dict[str, Any]:
    """Load domain configuration from JSON file"""
    domain_path = Path("seeds/domains") / f"{domain_id}.json"
    
    if not domain_path.exists():
        raise FileNotFoundError(f"Domain config not found: {domain_path}")
    
    with open(domain_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Example usage
if __name__ == "__main__":
    # Load domain config
    domain_config = load_domain_config("biohacking_longevity")
    
    # Initialize scorer
    scorer = OverlayScorer(domain_config)
    
    print(f"\n🔍 Dual-lens mode: {scorer.is_dual_lens()}")
    print(f"📋 Loaded overlays: {scorer.get_overlay_ids()}")
    
    # Test event scoring
    test_event = {
        'evidence_snippet': 'The protocol involved mechanism-based dosing with rapamycin to optimize anti-aging effects.'
    }
    
    event_scores = scorer.apply_event_scores(test_event)
    print(f"\n📊 Event scores:")
    for overlay_id, score in event_scores.items():
        print(f"   {overlay_id}: {score:+.1f}")
    
    # Test entity priority
    print(f"\n🎯 Entity priorities:")
    for entity_type in ['compound', 'pathway', 'target', 'assay']:
        for overlay_id in scorer.get_overlay_ids():
            priority = scorer.apply_entity_priority(entity_type, overlay_id)
            print(f"   {overlay_id} / {entity_type}: {priority}x")
    
    # Test bucketing
    print(f"\n📦 Score bucketing:")
    for score in [95, 75, 55, 35, 15]:
        bucket = scorer.bucket_score(score, max_score=100)
        print(f"   Score {score} → {bucket}")
