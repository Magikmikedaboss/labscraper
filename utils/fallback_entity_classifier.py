"""
Fallback Entity Classification Module

Implements multi-stage fallback strategies for entity classification when primary methods fail.
This ensures comprehensive entity coverage even for edge cases and novel entities.

Usage:
    from fallback_entity_classifier import FallbackEntityClassifier
    
    classifier = FallbackEntityClassifier(domain="construction_science")
    entities = classifier.apply_fallback_classification(text, existing_entities=[])
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import Counter
import logging

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class CandidateEntity:
    text: str
    start_pos: int
    end_pos: int
    confidence: float
    source: str

class FallbackEntityClassifier:
    """Multi-stage fallback entity classifier for improved coverage"""
    
    def __init__(self, domain: str = "construction"):
        self.domain = domain
        self.seeds = self._load_seeds()
        self.patterns = self._load_fallback_patterns()
        self.context_rules = self._load_context_rules()
        
    def _load_seeds(self) -> Dict:
        """Load seed data for fallback classification"""
        seeds = {}
        seeds_dir = Path(__file__).resolve().parent.parent / "seeds"        
        if seeds_dir.exists():
            # Load JSON seeds
            for json_file in seeds_dir.glob("*.json"):
                try:
                    seeds[json_file.stem] = json.loads(json_file.read_text(encoding="utf-8"))
                except Exception as e:
                    logger.warning(f"Failed to load JSON seed {json_file}: {e}")
            
            # Load ontology seeds
            seeds['ontology'] = {}
            base_dir = seeds_dir / "base"
            if base_dir.exists():
                for ontology_dir in base_dir.glob("*"):
                    if ontology_dir.is_dir():
                        ontology_name = ontology_dir.name
                        seeds['ontology'][ontology_name] = {}
                        for txt_file in ontology_dir.glob("*.txt"):
                            try:
                                entity_type = txt_file.stem
                                content = txt_file.read_text(encoding="utf-8")
                                entities = [line.strip() for line in content.splitlines() 
                                          if line.strip() and not line.startswith('#')]
                                seeds['ontology'][ontology_name][entity_type] = entities
                            except Exception as e:
                                logger.warning(f"Failed to load ontology {txt_file}: {e}")
        
        return seeds
    
    def _load_fallback_patterns(self) -> Dict:
        """Load fallback patterns for entity detection"""
        return {
            'construction': {
                'material_patterns': [
                    r'\b(?:high[-\s]?strength|reinforced|prestressed|fiber[-\s]?reinforced|carbon[-\s]?fiber|glass[-\s]?fiber)\s+(?:concrete|steel|polymer)\b',
                    r'\b(?:structural|load[-\s]?bearing|bearing|supporting)\s+(?:beam|column|wall|slab)\b',
                    r'\b(?:thermal|acoustic|fire|water|vapor)\s+(?:insulation|barrier|resistance|proof)\b',
                    r'\b(?:sealant|adhesive|coating|paint|finish)\b',
                    r'\b(?:aggregate|gravel|sand|cement|mortar|grout)\b'
                ],
                'system_patterns': [
                    r'\b(?:load[-\s]?bearing|structural|supporting|bearing)\s+(?:system|assembly|framework)\b',
                    r'\b(?:foundation|footing|pile|raft|slab)\b',
                    r'\b(?:roofing|cladding|façade|curtain\s+wall)\b',
                    r'\b(?:HVAC|plumbing|electrical|mechanical)\s+(?:system|installation)\b',
                    r'\b(?:seismic|wind|snow|live|dead)\s+(?:load|resistance)\b'
                ],
                'environment_patterns': [
                    r'\b(?:corrosive|harsh|extreme|aggressive)\s+(?:environment|condition)\b',
                    r'\b(?:marine|coastal|industrial|urban|rural)\s+(?:environment|exposure)\b',
                    r'\b(?:freeze[-\s]?thaw|thermal|moisture|humidity)\s+(?:cycle|variation)\b',
                    r'\b(?:UV|ultraviolet|solar|weathering)\s+(?:exposure|degradation)\b',
                    r'\b(?:chemical|biological|physical)\s+(?:attack|degradation)\b'
                ],
                'failure_patterns': [
                    r'\b(?:structural|mechanical|material)\s+(?:failure|collapse|buckling)\b',
                    r'\b(?:cracking|crack|fissure|fracture|split)\b',
                    r'\b(?:corrosion|rust|oxidation|deterioration)\b',
                    r'\b(?:deflection|deformation|distortion|sagging)\b',
                    r'\b(?:leakage|water\s+intrusion|moisture\s+damage)\b'
                ]
            },
            'biomedical': {
                'compound_patterns': [
                    r'\b(?:small[-\s]?molecule|peptide|protein|antibody|enzyme|inhibitor|activator)\b',
                    r'\b(?:drug|compound|molecule|agent|substance)\s+(?:X\d+|[A-Z]{2,}\d+)\b',
                    r'\b(?:IC50|EC50|KD|Ki|IC90|EC90)\s*[<>=]?\s*\d+[\s\w]*\b',
                    r'\b(?:potent|effective|active|inactive|weak)\s+(?:compound|drug|inhibitor)\b',
                    r'\b(?:synthetic|natural|organic|inorganic)\s+(?:compound|molecule)\b'
                ],
                'target_patterns': [
                    r'\b(?:protein|enzyme|receptor|channel|transporter)\s+(?:[A-Z][A-Z0-9]+)\b',
                    r'\b(?:gene|mutation|variant|polymorphism)\s+(?:[A-Z][A-Z0-9]+)\b',
                    r'\b(?:cell|tissue|organ)\s+(?:line|type|specific)\b',
                    r'\b(?:pathway|signal|cascade|network)\s+(?:[A-Z][A-Z0-9]+)\b',
                    r'\b(?:binding|interaction|expression|activity)\s+(?:assay|test)\b'
                ],
                'assay_patterns': [
                    r'\b(?:ELISA|HPLC|LC-MS|MS/MS|NMR|X-ray|crystallography)\b',
                    r'\b(?:in\s+vitro|in\s+vivo|ex\s+vivo)\s+(?:assay|test|experiment)\b',
                    r'\b(?:dose[-\s]?response|time[-\s]?course|kinetic)\s+(?:study|assay)\b',
                    r'\b(?:cell[-\s]?based|biochemical|functional)\s+(?:assay|screen)\b',
                    r'\b(?:high[-\s]?throughput|HTS|screening)\s+(?:assay|platform)\b'
                ]
            }
        }
    
    def _load_context_rules(self) -> Dict:
        """Load context-based classification rules"""
        return {
            'construction': {
                'material_keywords': [
                    'concrete', 'steel', 'wood', 'glass', 'brick', 'masonry', 'insulation',
                    'sealant', 'coating', 'paint', 'aggregate', 'cement', 'mortar'
                ],
                'system_keywords': [
                    'beam', 'column', 'wall', 'slab', 'foundation', 'roof', 'floor',
                    'frame', 'structure', 'assembly', 'component'
                ],
                'environment_keywords': [
                    'temperature', 'humidity', 'corrosion', 'exposure', 'weathering',
                    'freeze', 'thaw', 'UV', 'solar', 'marine', 'industrial'
                ],
                'failure_keywords': [
                    'failure', 'collapse', 'crack', 'fracture', 'corrosion', 'deterioration',
                    'deflection', 'deformation', 'leakage', 'damage', 'buckling'
                ]
            },
            'biomedical': {
                'compound_keywords': [
                    'compound', 'drug', 'molecule', 'inhibitor', 'activator', 'ligand',
                    'substrate', 'product', 'metabolite', 'peptide', 'protein'
                ],
                'target_keywords': [
                    'protein', 'enzyme', 'receptor', 'channel', 'transporter', 'gene',
                    'mutation', 'variant', 'cell', 'tissue', 'organ'
                ],
                'assay_keywords': [
                    'assay', 'test', 'experiment', 'screen', 'analysis', 'measurement',
                    'IC50', 'EC50', 'KD', 'Ki', 'activity', 'binding'
                ]
            }
        }
    
    def normalize_domain(self, domain: Optional[str] = None) -> str:
        """Normalize domain name for pattern lookups (removes _science, underscores)"""
        d = domain if domain is not None else self.domain
        return d.replace('_science', '').replace('_', '')

    def extract_candidate_entities(self, text: str) -> List[CandidateEntity]:
        """Extract candidate entities using various patterns"""
        candidates = []
        text_lower = text.lower()
        
        # Extract using domain-specific patterns
        pattern_domain = self.normalize_domain()
        if pattern_domain in self.patterns:
            for entity_type, patterns in self.patterns[pattern_domain].items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                    for match in matches:
                        candidates.append(CandidateEntity(
                            text=match.group(0),
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=0.6,
                            source=f"pattern_{entity_type}"
                        ))
        
        # Extract capitalized phrases (potential entity names)
        capitalized_phrases = self._extract_capitalized_phrases(text)
        candidates.extend(capitalized_phrases)
        
        # Extract alphanumeric codes (potential identifiers)
        codes = self._extract_alphanumeric_codes(text)
        candidates.extend(codes)
        
        return candidates
    
    def _extract_capitalized_phrases(self, text: str) -> List[CandidateEntity]:
        """Extract capitalized phrases that might be entity names"""
        candidates = []
        
        # Pattern for capitalized phrases (2-4 words)
        pattern = r'\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
        matches = re.finditer(pattern, text)
        
        for match in matches:
            phrase = match.group(0)
            # Filter out common non-entity phrases
            if self._is_likely_entity_phrase(phrase):
                candidates.append(CandidateEntity(
                    text=phrase,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.4,
                    source="capitalized_phrase"
                ))
        
        return candidates
    
    def _is_likely_entity_phrase(self, phrase: str) -> bool:
        """Check if a capitalized phrase is likely an entity name"""
        phrase_lower = phrase.lower()
        
        # Common non-entity prefixes/suffixes to filter out
        non_entity_patterns = [
            r'^(?:the|a|an|this|that|these|those|our|your|my|his|her|its)\b',
            r'\b(?:study|analysis|result|data|method|approach|technique|process|system)\b$',
            r'\b(?:based|related|associated|involved|including|containing)\b',
            r'\b(?:from|with|for|by|on|in|at|to|of|as|is|are|was|were)\b'
        ]
        
        for pattern in non_entity_patterns:
            if re.search(pattern, phrase_lower):
                return False
        
        # Check if it contains likely entity keywords
        if self.domain in self.context_rules:
            keywords = []
            for keyword_list in self.context_rules[self.domain].values():
                keywords.extend(keyword_list)
            
            keyword_count = sum(1 for keyword in keywords if keyword in phrase_lower)
            if keyword_count >= 1:
                return True
        
        # If it's a proper noun phrase (multiple capitalized words), likely an entity
        words = phrase.split()
        if len(words) >= 2 and all(word[0].isupper() for word in words):
            return True
        
        return False
    
    def _extract_alphanumeric_codes(self, text: str) -> List[CandidateEntity]:
        """Extract alphanumeric codes that might be identifiers"""
        candidates = []
        
        # Pattern for alphanumeric codes (e.g., ABC123, X-1234, compound-5)
        pattern = r'\b(?:[A-Z]{1,3}[-\s]?[0-9]{2,4}|[A-Z]{2,}[0-9]+|[0-9]+[A-Z]{1,3})\b'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            code = match.group(0)
            candidates.append(CandidateEntity(
                text=code,
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.3,
                source="alphanumeric_code"
            ))
        
        return candidates
    
    def classify_candidates(self, candidates: List[CandidateEntity], text: str) -> List[Dict]:
        """Classify candidate entities into specific types"""
        classified = []
        
        for candidate in candidates:
            entity_type = self._classify_entity_type(candidate.text, text)
            if entity_type:
                classified.append({
                    'entity_type': entity_type,
                    'entity_name': candidate.text,
                    'entity_variant': None,
                    'confidence': candidate.confidence,
                    'source': candidate.source,
                    'position': (candidate.start_pos, candidate.end_pos)
                })
        
        return classified
    
    def _classify_entity_type(self, entity_text: str, context: str) -> Optional[str]:
        """Classify entity type based on text and context"""
        entity_lower = entity_text.lower()
        context_lower = context.lower()

        # Normalize domain for all lookups
        domain_normalized = self.normalize_domain()

        if domain_normalized not in self.context_rules:
            return None

        rules = self.context_rules[domain_normalized]

        # Check for exact matches in seeds
        if 'ontology' in self.seeds and domain_normalized in self.seeds['ontology']:
            ontology = self.seeds['ontology'][domain_normalized]
            for entity_type, entities in ontology.items():
                if entity_lower in [e.lower() for e in entities]:
                    return entity_type

        # Check context-based classification
        for entity_type, keywords in rules.items():
            keyword_matches = sum(1 for keyword in keywords if keyword in entity_lower or keyword in context_lower)
            if keyword_matches >= 2:
                return entity_type

        # Pattern-based classification
        if domain_normalized in self.patterns:
            for entity_type, patterns in self.patterns[domain_normalized].items():
                for pattern in patterns:
                    if re.search(pattern, entity_lower, re.IGNORECASE):
                        return entity_type

        return None
    
    def apply_fallback_classification(self, text: str, existing_entities: List[Dict]) -> List[Dict]:
        """
        Apply fallback classification to improve entity coverage
        
        Args:
            text: Input text to analyze
            existing_entities: Already extracted entities to avoid duplicates
            
        Returns:
            Enhanced list of entities including fallback classifications
        """
        # Extract candidate entities
        candidates = self.extract_candidate_entities(text)
        
        # Classify candidates
        classified = self.classify_candidates(candidates, text)
        
        # Filter out duplicates with existing entities
        existing_names = {e['entity_name'].lower() for e in existing_entities}
        new_entities = [e for e in classified if e['entity_name'].lower() not in existing_names]
        
        # Combine with existing entities
        all_entities = existing_entities + new_entities
        
        # Sort by confidence descending
        all_entities.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
        
        return all_entities    
    def get_coverage_improvement(self, original_entities: List[Dict], enhanced_entities: List[Dict]) -> Dict:
        """Calculate coverage improvement metrics"""
        original_count = len(original_entities)
        enhanced_count = len(enhanced_entities)
        new_count = enhanced_count - original_count
        
        original_types = set(e['entity_type'] for e in original_entities)
        enhanced_types = set(e['entity_type'] for e in enhanced_entities)
        new_types = enhanced_types - original_types
        
        return {
            'original_count': original_count,
            'enhanced_count': enhanced_count,
            'new_entities': new_count,
            'coverage_improvement': round((new_count / original_count * 100) if original_count > 0 else 0, 2),
            'original_types': list(original_types),
            'enhanced_types': list(enhanced_types),
            'new_types': list(new_types)
        }

# Backward compatibility function
def apply_fallback_classification(text: str, existing_entities: List[Dict], domain: str = "methods_tooling") -> List[Dict]:
    """
    Backward compatible fallback classification function
    
    Returns enhanced entity list with fallback classifications
    """
    classifier = FallbackEntityClassifier(domain=domain)
    return classifier.apply_fallback_classification(text, existing_entities)

# Example usage and testing
if __name__ == "__main__":
    print("Testing Fallback Entity Classifier")
    print("=" * 50)
    
    # Test with construction science
    construction_text = """
    The high-strength concrete beam experienced significant cracking after 10 years 
    of exposure to marine environments. The structural failure was attributed to 
    chloride-induced corrosion of the steel reinforcement. Temperature variations 
    caused thermal expansion and contraction, leading to additional stress on the 
    masonry walls. The XYZ-123 compound showed promising results in preventing 
    corrosion in laboratory tests.
    """
    
    classifier = FallbackEntityClassifier(domain="construction_science")
    candidates = classifier.extract_candidate_entities(construction_text)
    
    print(f"Extracted {len(candidates)} candidate entities")
    for candidate in candidates[:10]:  # Show first 10
        print(f"  {candidate.text} ({candidate.source}, confidence: {candidate.confidence})")
    
    classified = classifier.classify_candidates(candidates, construction_text)
    print(f"\nClassified {len(classified)} entities")
    for entity in classified[:10]:  # Show first 10
        print(f"  {entity['entity_type']}: {entity['entity_name']} (confidence: {entity['confidence']})")
    
    # Test with biomedical domain
    print("\n" + "=" * 50)
    print("Testing with biomedical domain")
    
    biomedical_text = """
    The compound ABC-1234 showed potent inhibition of the target protein XYZ with 
    an IC50 of 10nM in the ELISA assay. The in vitro study demonstrated significant 
    activity against the disease pathway. The XYZ-567 molecule exhibited weak 
    binding in the biochemical assay.
    """
    
    bio_classifier = FallbackEntityClassifier(domain="biomedical")
    bio_candidates = bio_classifier.extract_candidate_entities(biomedical_text)
    
    print(f"Extracted {len(bio_candidates)} candidate entities")
    for candidate in bio_candidates[:10]:  # Show first 10
        print(f"  {candidate.text} ({candidate.source}, confidence: {candidate.confidence})")
    
    bio_classified = bio_classifier.classify_candidates(bio_candidates, biomedical_text)
    
    for entity in bio_classified[:10]:  # Show first 10
        print(f"  {entity['entity_type']}: {entity['entity_name']} (confidence: {entity['confidence']})")