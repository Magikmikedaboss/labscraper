"""
Axon Labs Domain Profile System
Provides domain-specific lenses for research intelligence without rewriting the core engine.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DomainProfile:
    """
    Domain profile for research intelligence lens.
    
    Attributes:
        id: Unique domain identifier
        name: Human-readable domain name
        description: Domain description and disclaimers
        claims_mode: Always "observational_only" for Axon Labs
        domain_profile_version: Version for reproducibility
        seed_overlays: Seed file preferences for this domain
        exclusions: Terms and document types to exclude
        pattern_emphasis: Soft multipliers for pattern scores
        language: Allowed and forbidden language for this domain
    """
    id: str
    name: str
    description: str
    claims_mode: str
    domain_profile_version: str
    seed_overlays: Dict[str, Any]
    exclusions: Dict[str, Any]
    pattern_emphasis: Dict[str, float]
    language: Dict[str, List[str]]

    def is_excluded_text(self, text: str) -> bool:
        """
        Return True if text contains any excluded term (case-insensitive, word-boundary).
        
        Args:
            text: Text to check for excluded terms
            
        Returns:
            True if text should be excluded, False otherwise
        """
        terms = self.exclusions.get("terms", [])
        if not terms:
            return False
        
        t = text.lower()
        for term in terms:
            # Use word boundary for short terms; loose match for multiword phrases
            term_l = term.lower().strip()
            if not term_l:
                continue
            
            if " " in term_l:
                # Multiword phrase - use substring match
                if term_l in t:
                    return True
            else:
                # Single word - use word boundary
                if re.search(r"\b" + re.escape(term_l) + r"\b", t):
                    return True
        
        return False

    def emphasize_pattern(self, pattern_type: str, score: float) -> float:
        """
        Apply domain emphasis multiplier (soft weighting) to an existing pattern score.
        
        This is a lens, not a rewrite - it gently adjusts scores based on domain focus.
        
        Args:
            pattern_type: Pattern type (convergence, escalation, etc.)
            score: Original pattern health score
            
        Returns:
            Adjusted score with domain emphasis applied
        """
        mult = float(self.pattern_emphasis.get(pattern_type, 1.0))
        return score * mult

    def is_forbidden_language(self, text: str) -> bool:
        """
        Check if text contains forbidden language for this domain.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains forbidden language
        """
        forbidden = self.language.get("forbidden", [])
        if not forbidden:
            return False
        
        t = text.lower()
        for phrase in forbidden:
            phrase_l = phrase.lower().strip()
            if not phrase_l:
                continue
            
            if phrase_l in t:
                return True
        
        return False

    def get_preferred_entity_types(self) -> List[str]:
        """
        Get list of preferred entity types for this domain.
        
        Returns:
            List of entity type strings
        """
        return self.seed_overlays.get("prefer_types", [])

    def get_seed_files(self) -> List[str]:
        """
        Get list of seed files to include for this domain.
        
        Returns:
            List of seed file names
        """
        return self.seed_overlays.get("include_files", [])


def load_domain_profile(path: str) -> DomainProfile:
    """
    Load a domain profile from a JSON file.
    
    Args:
        path: Path to domain profile JSON file
        
    Returns:
        DomainProfile instance
        
    Raises:
        ValueError: If required fields are missing
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Minimal validation with safe defaults
    required = ["id", "name", "description"]
    for k in required:
        if k not in data or not str(data[k]).strip():
            raise ValueError(f"Domain profile missing required field: {k} ({path})")

    return DomainProfile(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        claims_mode=data.get("claims_mode", "observational_only"),
        domain_profile_version=data.get("domain_profile_version", "v1"),
        seed_overlays=data.get("seed_overlays", {}),
        exclusions=data.get("exclusions", {}),
        pattern_emphasis=data.get("pattern_emphasis", {}),
        language=data.get("language", {"allowed": [], "forbidden": []}),
    )


def load_all_domains(domains_dir: str) -> Dict[str, DomainProfile]:
    """
    Load all domain profiles from a directory.
    
    Args:
        domains_dir: Path to directory containing domain JSON files
        
    Returns:
        Dictionary mapping domain IDs to DomainProfile instances
        
    Raises:
        ValueError: If duplicate domain IDs are found
    """
    domains: Dict[str, DomainProfile] = {}
    
    if not os.path.exists(domains_dir):
        return domains
    
    for fname in os.listdir(domains_dir):
        if not fname.endswith(".json"):
            continue
        
        prof = load_domain_profile(os.path.join(domains_dir, fname))
        
        if prof.id in domains:
            raise ValueError(f"Duplicate domain id: {prof.id}")
        
        domains[prof.id] = prof
    
    return domains


def get_domain_by_id(domain_id: str, domains_dir: str = "seeds/domains") -> Optional[DomainProfile]:
    """
    Get a specific domain profile by ID.
    
    Args:
        domain_id: Domain identifier
        domains_dir: Path to domains directory
        
    Returns:
        DomainProfile if found, None otherwise
    """
    domains = load_all_domains(domains_dir)
    return domains.get(domain_id)


# Example usage
if __name__ == "__main__":
    # Load all domains
    domains = load_all_domains("seeds/domains")
    
    print("="*70)
    print("AXON LABS DOMAIN PROFILES")
    print("="*70)
    
    for domain_id, profile in domains.items():
        print(f"\n{profile.name} ({profile.id})")
        print(f"  Version: {profile.domain_profile_version}")
        print(f"  Claims Mode: {profile.claims_mode}")
        print(f"  Description: {profile.description[:100]}...")
        print(f"  Preferred Types: {', '.join(profile.get_preferred_entity_types())}")
        print(f"  Exclusions: {len(profile.exclusions.get('terms', []))} terms")
        print(f"  Pattern Emphasis: {profile.pattern_emphasis}")
    
    print(f"\n✅ Loaded {len(domains)} domain profiles")
    
    # Example: Test exclusion
    if "stem_cells_regen" in domains:
        stem_domain = domains["stem_cells_regen"]
        test_texts = [
            "MSC differentiation in vitro",
            "Visit our stem cell spa for guaranteed results",
            "iPSC-derived organoids show promise"
        ]
        
        print(f"\n🧪 Testing exclusions for {stem_domain.name}:")
        for text in test_texts:
            excluded = stem_domain.is_excluded_text(text)
            status = "❌ EXCLUDED" if excluded else "✅ ALLOWED"
            print(f"  {status}: {text}")
