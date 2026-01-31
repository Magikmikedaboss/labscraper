"""
Integrated Entity Extraction System

Combines enhanced entity extraction with fallback classification for maximum coverage and accuracy.
This module provides a unified interface for entity extraction across all domains.

Usage:
    from integrated_entity_system import IntegratedEntitySystem
    
    system = IntegratedEntitySystem(domain="construction_science")
    entities = system.extract_entities(text, title=title)
    coverage_stats = system.get_coverage_stats()
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

# Import the enhanced modules
from .enhanced_entity_extractor import EnhancedEntityExtractor, Entity
from .fallback_entity_classifier import FallbackEntityClassifier, apply_fallback_classification

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    entities: List[Dict]
    coverage_stats: Dict
    processing_time: float
    confidence_distribution: Dict

class IntegratedEntitySystem:
    """Unified entity extraction system with enhanced accuracy and coverage"""
    
    def __init__(self, domain: str = "methods_tooling", enable_fallback: bool = True):
        self.domain = domain
        self.enable_fallback = enable_fallback
        self.enhanced_extractor = EnhancedEntityExtractor(domain=domain)
        self.fallback_classifier = FallbackEntityClassifier(domain=domain) if enable_fallback else None
        
        # Statistics tracking
        self.stats = {
            'total_extractions': 0,
            'fallback_used': 0,
            'coverage_improvements': [],
            'confidence_scores': []
        }
    
    def extract_entities(self, text: str, title: str = "") -> List[Dict]:
        """
        Extract entities using the integrated system
        
        Process:
        1. Use enhanced entity extractor (primary method)
        2. Apply fallback classification if enabled (secondary method)
        3. Combine and deduplicate results
        4. Calculate coverage statistics
        """
        import time
        start_time = time.time()
        
        # Step 1: Enhanced extraction
        enhanced_entities = self.enhanced_extractor.extract_entities(text, title)
        enhanced_dict = [asdict(entity) for entity in enhanced_entities]
        
        # Step 2: Fallback classification (if enabled and needed)
        if self.enable_fallback and len(enhanced_dict) < 3:  # Use fallback if low coverage
            fallback_entities = apply_fallback_classification(text, enhanced_dict, self.domain)
            self.stats['fallback_used'] += 1
        else:
            fallback_entities = enhanced_dict
        
        # Step 3: Deduplicate and sort by confidence
        final_entities = self._deduplicate_entities(fallback_entities)
        
        # Step 4: Calculate statistics
        processing_time = time.time() - start_time
        coverage_stats = self._calculate_coverage_stats(final_entities, enhanced_dict, fallback_entities)
        confidence_distribution = self._get_confidence_distribution(final_entities)
        
        # Update global stats
        self.stats['total_extractions'] += 1
        self.stats['coverage_improvements'].append(coverage_stats.get('coverage_improvement', 0))
        self.stats['confidence_scores'].extend([e['confidence'] for e in final_entities])
        
        return final_entities
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Deduplicate entities by type and name, keeping highest confidence"""
        seen = set()
        deduplicated = []
        
        # Sort by confidence descending (non-mutating)
        sorted_entities = sorted(entities, key=lambda x: x['confidence'], reverse=True)
        for entity in sorted_entities:
            key = (entity['entity_type'], entity['entity_name'], entity.get('entity_variant'))
            if key not in seen:
                seen.add(key)
                deduplicated.append(entity)
        
        return deduplicated
    
    def _calculate_coverage_stats(self, final_entities: List[Dict], enhanced_entities: List[Dict], fallback_entities: List[Dict]) -> Dict:
        """Calculate coverage improvement statistics"""
        enhanced_count = len(enhanced_entities)
        fallback_count = len(fallback_entities)
        final_count = len(final_entities)
        
        # Calculate type coverage
        enhanced_types = set(e['entity_type'] for e in enhanced_entities)
        final_types = set(e['entity_type'] for e in final_entities)
        
        # Calculate confidence metrics
        avg_confidence = sum(e['confidence'] for e in final_entities) / len(final_entities) if final_entities else 0
        high_confidence_count = sum(1 for e in final_entities if e['confidence'] >= 0.8)
        medium_confidence_count = sum(1 for e in final_entities if 0.5 <= e['confidence'] < 0.8)
        low_confidence_count = sum(1 for e in final_entities if e['confidence'] < 0.5)
        
        return {
            'enhanced_count': enhanced_count,
            'fallback_count': fallback_count,
            'final_count': final_count,
            'coverage_improvement': round(((final_count - enhanced_count) / enhanced_count * 100) if enhanced_count > 0 else 0, 2),
            'enhanced_types': list(enhanced_types),
            'final_types': list(final_types),
            'new_types': list(final_types - enhanced_types),
            'avg_confidence': round(avg_confidence, 2),
            'high_confidence_count': high_confidence_count,
            'medium_confidence_count': medium_confidence_count,
            'low_confidence_count': low_confidence_count,
            'confidence_distribution': {
                'high': high_confidence_count,
                'medium': medium_confidence_count,
                'low': low_confidence_count
            }
        }
    
    def _get_confidence_distribution(self, entities: List[Dict]) -> Dict:
        """Get confidence score distribution"""
        distribution = defaultdict(int)
        for entity in entities:
            confidence = entity['confidence']
            if confidence >= 0.8:
                distribution['high'] += 1
            elif confidence >= 0.5:
                distribution['medium'] += 1
            else:
                distribution['low'] += 1
        return dict(distribution)
    
    def get_coverage_stats(self) -> Dict:
        """Get overall system coverage statistics"""
        if not self.stats['coverage_improvements']:
            return {
                'total_extractions': self.stats['total_extractions'],
                'fallback_used': self.stats['fallback_used'],
                'avg_coverage_improvement': 0,
                'avg_confidence': 0,
                'coverage_by_type': {}
            }
        
        avg_improvement = sum(self.stats['coverage_improvements']) / len(self.stats['coverage_improvements'])
        avg_confidence = sum(self.stats['confidence_scores']) / len(self.stats['confidence_scores']) if self.stats['confidence_scores'] else 0
        
        return {
            'total_extractions': self.stats['total_extractions'],
            'fallback_used': self.stats['fallback_used'],
            'fallback_usage_rate': round((self.stats['fallback_used'] / self.stats['total_extractions'] * 100) if self.stats['total_extractions'] > 0 else 0, 2),
            'avg_coverage_improvement': round(avg_improvement, 2),
            'avg_confidence': round(avg_confidence, 2),
            'coverage_by_type': self._get_type_coverage_breakdown()
        }
    
    def _get_type_coverage_breakdown(self) -> Dict:
        """Get coverage breakdown by entity type"""
        # This would need to be implemented based on actual usage patterns
        # For now, return a placeholder structure
        return {
            'material': {'count': 0, 'coverage': 0},
            'system': {'count': 0, 'coverage': 0},
            'environment': {'count': 0, 'coverage': 0},
            'compound': {'count': 0, 'coverage': 0},
            'target': {'count': 0, 'coverage': 0},
            'assay': {'count': 0, 'coverage': 0}
        }
    
    def validate_entity_quality(self, entities: List[Dict]) -> Dict:
        """Validate entity extraction quality"""
        if not entities:
            return {
                'quality_score': 0,
                'issues': ['No entities extracted'],
                'recommendations': ['Check input text quality', 'Verify domain configuration']
            }
        
        # Calculate quality metrics
        avg_confidence = sum(e['confidence'] for e in entities) / len(entities)
        high_confidence_ratio = sum(1 for e in entities if e['confidence'] >= 0.8) / len(entities)
        type_diversity = len(set(e['entity_type'] for e in entities)) / len(entities) if entities else 0
        
        # Quality scoring
        quality_score = min(100, (avg_confidence * 50) + (high_confidence_ratio * 30) + (type_diversity * 20))
        
        # Identify issues
        issues = []
        recommendations = []
        
        if avg_confidence < 0.6:
            issues.append(f"Low average confidence: {avg_confidence:.2f}")
            recommendations.append("Consider enabling fallback classification")
        
        if high_confidence_ratio < 0.3:
            issues.append(f"Low high-confidence entity ratio: {high_confidence_ratio:.2f}")
            recommendations.append("Review seed data quality")
        
        if type_diversity < 0.2:
            issues.append(f"Low entity type diversity: {type_diversity:.2f}")
            recommendations.append("Expand seed ontologies")
        
        return {
            'quality_score': round(quality_score, 2),
            'issues': issues,
            'recommendations': recommendations,
            'metrics': {
                'avg_confidence': round(avg_confidence, 2),
                'high_confidence_ratio': round(high_confidence_ratio, 2),
                'type_diversity': round(type_diversity, 2)
            }
        }
    
    def export_entities_for_export(self, entities: List[Dict]) -> List[Dict]:
        """
        Format entities for export system compatibility
        
        Ensures entities match the expected format for the export system
        """
        formatted_entities = []
        
        for entity in entities:
            formatted_entity = {
                'entity_type': entity['entity_type'],
                'entity_name': entity['entity_name'],
                'entity_variant': entity.get('entity_variant'),
                'confidence': entity['confidence'],
                'source': entity.get('source', 'integrated_system'),
                'role': self._determine_entity_role(entity)
            }
            
            # Add context window if available
            if 'context_window' in entity:
                formatted_entity['context_window'] = entity['context_window']
            
            # Add position if available
            if 'position' in entity:
                formatted_entity['position'] = entity['position']
            
            formatted_entities.append(formatted_entity)
        
        return formatted_entities
    
    def _determine_entity_role(self, entity: Dict) -> str:
        """Determine entity role based on type and confidence"""
        entity_type = entity['entity_type']
        confidence = entity['confidence']
        
        # High-confidence primary entities
        if confidence >= 0.8:
            if entity_type in ['material', 'compound', 'target', 'assay']:
                return 'primary'
            else:
                return 'context'
        
        # Medium-confidence entities
        elif confidence >= 0.5:
            if entity_type in ['system', 'environment', 'pathway']:
                return 'context'
            else:
                return 'supporting'
        
        # Low-confidence entities
        else:
            return 'supporting'

# Backward compatibility function
def extract_entities(text: str, seeds: Dict, title: str = "", domain: str = "methods_tooling") -> List[Dict]:
    """
    Backward compatible entity extraction function
    
    Uses the integrated system for improved results
    """
    system = IntegratedEntitySystem(domain=domain)
    entities = system.extract_entities(text, title)
    return system.export_entities_for_export(entities)

# Example usage and testing
if __name__ == "__main__":
    print("Testing Integrated Entity System")
    print("=" * 60)
    
    # Test with construction science
    print("Construction Science Test:")
    construction_text = """
    The high-strength concrete beam experienced significant cracking after 10 years 
    of exposure to marine environments. The structural failure was attributed to 
    chloride-induced corrosion of the steel reinforcement. Temperature variations 
    caused thermal expansion and contraction, leading to additional stress on the 
    masonry walls. The XYZ-123 compound showed promising results in preventing 
    corrosion in laboratory tests. The load-bearing capacity was reduced by 40%.
    """
    
    construction_system = IntegratedEntitySystem(domain="construction_science")
    construction_entities = construction_system.extract_entities(construction_text, "Test Construction Study")
    
    print(f"Extracted {len(construction_entities)} entities")
    for entity in construction_entities:
        print(f"  {entity['entity_type']}: {entity['entity_name']} (confidence: {entity['confidence']}, role: {entity.get('role')})")
    
    construction_stats = construction_system.get_coverage_stats()
    construction_quality = construction_system.validate_entity_quality(construction_entities)
    
    print(f"\nCoverage Stats: {construction_stats}")
    print(f"Quality Assessment: {construction_quality}")
    
    # Test with biomedical domain
    print("\n" + "=" * 60)
    print("Biomedical Domain Test:")
    
    biomedical_text = """
    The compound ABC-1234 showed potent inhibition of the target protein XYZ with 
    an IC50 of 10nM in the ELISA assay. The in vitro study demonstrated significant 
    activity against the disease pathway. The XYZ-567 molecule exhibited weak 
    binding in the biochemical assay. The results suggest potential therapeutic applications.
    """
    
    biomedical_system = IntegratedEntitySystem(domain="methods_tooling")
    biomedical_entities = biomedical_system.extract_entities(biomedical_text, "Test Biomedical Study")
    
    print(f"Extracted {len(biomedical_entities)} entities")
    for entity in biomedical_entities:
        print(f"  {entity['entity_type']}: {entity['entity_name']} (confidence: {entity['confidence']}, role: {entity['role']})")
    
    biomedical_stats = biomedical_system.get_coverage_stats()
    biomedical_quality = biomedical_system.validate_entity_quality(biomedical_entities)
    
    print(f"\nCoverage Stats: {biomedical_stats}")
    print(f"Quality Assessment: {biomedical_quality}")
    
    # Test system statistics
    print("\n" + "=" * 60)
    print("System Statistics:")
    print(f"Construction system stats: {construction_system.get_coverage_stats()}")
    print(f"Biomedical system stats: {biomedical_system.get_coverage_stats()}")