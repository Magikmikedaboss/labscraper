"""
Test Script for Enhanced Entity Extraction System

This script validates the enhanced entity extraction system and demonstrates
improvements in entity coverage and accuracy.

Usage:
    python utils/test_enhanced_entities.py
"""

import time
import json
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import asdict

# Import the enhanced modules
from utils.integrated_entity_system import IntegratedEntitySystem
from utils.enhanced_entity_extractor import EnhancedEntityExtractor
from utils.fallback_entity_classifier import FallbackEntityClassifier

def load_test_cases() -> Dict:
    """Load test cases for validation"""
    test_cases = {
        'construction_science': [
            {
                'name': 'Marine Environment Corrosion',
                'text': """
                The high-strength concrete beam experienced significant cracking after 10 years 
                of exposure to marine environments. The structural failure was attributed to 
                chloride-induced corrosion of the steel reinforcement. Temperature variations 
                caused thermal expansion and contraction, leading to additional stress on the 
                masonry walls. The XYZ-123 compound showed promising results in preventing 
                corrosion in laboratory tests. The load-bearing capacity was reduced by 40%.
                """,
                'expected_entities': ['concrete', 'beam', 'cracking', 'marine', 'corrosion', 'steel', 'reinforcement', 'structural failure', 'temperature', 'expansion', 'contraction', 'stress', 'masonry', 'walls', 'compound', 'laboratory', 'load-bearing', 'capacity']
            },
            {
                'name': 'Building Materials Performance',
                'text': """
                The thermal insulation performance of the building envelope was evaluated 
                under various environmental conditions. The vapor barrier showed excellent 
                resistance to moisture penetration, while the sealant maintained its 
                adhesion properties after 5 years of UV exposure. The fire-resistant 
                coating provided adequate protection during the fire test.
                """,
                'expected_entities': ['thermal insulation', 'building envelope', 'environmental conditions', 'vapor barrier', 'moisture penetration', 'sealant', 'adhesion', 'UV exposure', 'fire-resistant coating', 'fire test']
            }
        ],
        'biomedical': [
            {
                'name': 'Compound Activity Study',
                'text': """
                The compound ABC-1234 showed potent inhibition of the target protein XYZ with 
                an IC50 of 10nM in the ELISA assay. The in vitro study demonstrated significant 
                activity against the disease pathway. The XYZ-567 molecule exhibited weak 
                binding in the biochemical assay. The results suggest potential therapeutic applications.
                """,
                'expected_entities': ['compound', 'ABC-1234', 'inhibition', 'target protein', 'XYZ', 'IC50', 'ELISA assay', 'in vitro', 'activity', 'disease pathway', 'XYZ-567', 'molecule', 'weak binding', 'biochemical assay', 'therapeutic applications']
            },
            {
                'name': 'Drug Development Pipeline',
                'text': """
                The small molecule inhibitor demonstrated excellent pharmacokinetic properties 
                with a half-life of 12 hours. The dose-response curve showed an EC50 of 5nM, 
                indicating high potency. The compound was well-tolerated in animal models 
                with no observed toxicity at therapeutic doses.
                """,
                'expected_entities': ['small molecule inhibitor', 'pharmacokinetic', 'half-life', 'dose-response', 'EC50', 'potency', 'animal models', 'toxicity', 'therapeutic doses']
            }
        ]
    }
    return test_cases

def test_enhanced_extractor(domain: str, text: str) -> Dict:
    """Test the enhanced entity extractor"""
    extractor = EnhancedEntityExtractor(domain=domain)
    
    start_time = time.time()
    entities = extractor.extract_entities(text)
    processing_time = time.time() - start_time
    
    stats = extractor.get_entity_coverage_stats(entities)
    
    return {
        'entities': [asdict(entity) for entity in entities],
        'stats': stats,
        'processing_time': processing_time
    }

def test_fallback_classifier(domain: str, text: str, existing_entities: List[Dict]) -> Dict:
    """Test the fallback entity classifier"""
    classifier = FallbackEntityClassifier(domain=domain)
    
    start_time = time.time()
    enhanced_entities = classifier.apply_fallback_classification(text, existing_entities)
    processing_time = time.time() - start_time
    
    coverage_improvement = classifier.get_coverage_improvement(existing_entities, enhanced_entities)
    
    return {
        'enhanced_entities': enhanced_entities,
        'coverage_improvement': coverage_improvement,
        'processing_time': processing_time
    }

def test_integrated_system(domain: str, text: str, title: str = "") -> Dict:
    """Test the integrated entity system"""
    system = IntegratedEntitySystem(domain=domain)
    
    start_time = time.time()
    entities = system.extract_entities(text, title)
    processing_time = time.time() - start_time
    
    coverage_stats = system.get_coverage_stats()
    quality_assessment = system.validate_entity_quality(entities)
    
    return {
        'entities': entities,
        'coverage_stats': coverage_stats,
        'quality_assessment': quality_assessment,
        'processing_time': processing_time
    }

def calculate_coverage_score(extracted_entities: List[Dict], expected_entities: List[str]) -> Dict:
    """Calculate coverage score against expected entities"""
    extracted_names = {e['entity_name'].lower() for e in extracted_entities}
    expected_lower = [e.lower() for e in expected_entities]
    
    # Calculate exact matches
    exact_matches = sum(1 for name in extracted_names if name in expected_lower)
    
    # Calculate partial matches (substring)
    partial_matches = 0
    for name in extracted_names:
        for expected in expected_lower:
            if name != expected and (name in expected or expected in name):
                partial_matches += 1
                break
    
    total_expected = len(expected_entities)
    
    return {
        'exact_matches': exact_matches,
        'partial_matches': partial_matches,
        'total_expected': total_expected,
        'exact_coverage': round((exact_matches / total_expected * 100) if total_expected > 0 else 0, 2),
        'partial_coverage': round((partial_matches / total_expected * 100) if total_expected > 0 else 0, 2)
    }
def run_comprehensive_test():
    """Run comprehensive tests for all domains and systems"""
    print("🧪 Enhanced Entity Extraction System - Comprehensive Test")
    print("=" * 80)
    
    test_cases = load_test_cases()
    results = {}
    
    for domain, cases in test_cases.items():
        print(f"\n📋 Testing Domain: {domain.upper()}")
        print("-" * 60)
        
        domain_results = []
        
        for i, case in enumerate(cases, 1):
            print(f"\n  Test Case {i}: {case['name']}")
            print(f"  Text length: {len(case['text'])} characters")
            
            # Test enhanced extractor
            enhanced_result = test_enhanced_extractor(domain, case['text'])
            print(f"    Enhanced Extractor: {len(enhanced_result['entities'])} entities ({enhanced_result['processing_time']:.3f}s)")
            
            # Test fallback classifier
            fallback_result = test_fallback_classifier(domain, case['text'], enhanced_result['entities'])
            print(f"    Fallback Classifier: {len(fallback_result['enhanced_entities'])} entities ({fallback_result['processing_time']:.3f}s)")
            
            # Test integrated system
            integrated_result = test_integrated_system(domain, case['text'], case['name'])
            print(f"    Integrated System: {len(integrated_result['entities'])} entities ({integrated_result['processing_time']:.3f}s)")
            
            # Calculate coverage scores
            enhanced_coverage = calculate_coverage_score(enhanced_result['entities'], case['expected_entities'])
            integrated_coverage = calculate_coverage_score(integrated_result['entities'], case['expected_entities'])
            
            print(f"    Coverage - Enhanced: {enhanced_coverage['exact_coverage']}% exact, {enhanced_coverage['partial_coverage']}% partial")
            print(f"    Coverage - Integrated: {integrated_coverage['exact_coverage']}% exact, {integrated_coverage['partial_coverage']}% partial")
            
            # Quality assessment
            quality = integrated_result['quality_assessment']
            print(f"    Quality Score: {quality['quality_score']}/100")
            
            case_result = {
                'case_name': case['name'],
                'enhanced_result': enhanced_result,
                'fallback_result': fallback_result,
                'integrated_result': integrated_result,
                'enhanced_coverage': enhanced_coverage,
                'integrated_coverage': integrated_coverage,
                'quality_assessment': quality
            }
            
            domain_results.append(case_result)
        
        results[domain] = domain_results
    
    return results

def generate_test_report(results: Dict):
    """Generate a comprehensive test report"""
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("=" * 80)
    
    for domain, domain_results in results.items():
        print(f"\n🏗️  DOMAIN: {domain.upper()}")
        print("-" * 60)
        
        total_cases = len(domain_results)
        if total_cases == 0:
            print("  No test cases for this domain")
            continue
            
        total_enhanced_entities = sum(len(r['enhanced_result']['entities']) for r in domain_results)
        total_integrated_entities = sum(len(r['integrated_result']['entities']) for r in domain_results)
        
        avg_enhanced_coverage = sum(r['enhanced_coverage']['exact_coverage'] for r in domain_results) / total_cases
        avg_integrated_coverage = sum(r['integrated_coverage']['exact_coverage'] for r in domain_results) / total_cases
        avg_quality_score = sum(r['quality_assessment']['quality_score'] for r in domain_results) / total_cases        
        print(f"  Total Test Cases: {total_cases}")
        print(f"  Total Enhanced Entities: {total_enhanced_entities}")
        print(f"  Total Integrated Entities: {total_integrated_entities}")
        print(f"  Average Enhanced Coverage: {avg_enhanced_coverage:.1f}%")
        print(f"  Average Integrated Coverage: {avg_integrated_coverage:.1f}%")
        print(f"  Average Quality Score: {avg_quality_score:.1f}/100")
        
        # Coverage improvement
        coverage_improvement = avg_integrated_coverage - avg_enhanced_coverage
        print(f"  Coverage Improvement: +{coverage_improvement:.1f} percentage points")
        
        # Entity type diversity
        all_entity_types = set()
        for result in domain_results:
            for entity in result['integrated_result']['entities']:
                all_entity_types.add(entity['entity_type'])
        print(f"  Entity Types Detected: {len(all_entity_types)}")
        print(f"    {', '.join(sorted(all_entity_types))}")
    
    # Overall summary
    print(f"\n🎯 OVERALL SUMMARY")
    print("-" * 60)
    
    total_cases_all = sum(len(results[d]) for d in results)
    if total_cases_all == 0:
        print("  No test cases executed")
        return
    total_entities_all = sum(len(r['integrated_result']['entities']) for domain in results for r in results[domain])
    avg_quality_all = sum(r['quality_assessment']['quality_score'] for domain in results for r in results[domain]) / total_cases_all    
    print(f"  Total Test Cases: {total_cases_all}")
    print(f"  Total Entities Extracted: {total_entities_all}")
    print(f"  Average Quality Score: {avg_quality_all:.1f}/100")
    
    # Performance metrics
    total_time = sum(r['integrated_result']['processing_time'] for domain in results for r in results[domain])
    avg_time_per_case = total_time / total_cases_all if total_cases_all > 0 else 0
    print(f"  Average Processing Time: {avg_time_per_case:.3f} seconds per case")
    
    # Success criteria evaluation
    print(f"\n✅ SUCCESS CRITERIA EVALUATION")
    print("-" * 60)
    
    # Check if we achieved the target coverage improvement
    target_coverage = 70.0
    achieved_coverage = sum(r['integrated_coverage']['exact_coverage'] for domain in results for r in results[domain]) / total_cases_all
    
    print(f"  Target Entity Coverage: {target_coverage}%")
    print(f"  Achieved Entity Coverage: {achieved_coverage:.1f}%")
    print(f"  Coverage Goal: {'✅ MET' if achieved_coverage >= target_coverage else '❌ NOT MET'}")
    
    # Check quality score target
    target_quality = 85.0
    print(f"  Target Quality Score: {target_quality}/100")
    print(f"  Achieved Quality Score: {avg_quality_all:.1f}/100")
    print(f"  Quality Goal: {'✅ MET' if avg_quality_all >= target_quality else '❌ NOT MET'}")
    
    # Check processing time target
    target_time = 1.0  # 1 second per case
    print(f"  Target Processing Time: {target_time} seconds")
    print(f"  Achieved Processing Time: {avg_time_per_case:.3f} seconds")
    print(f"  Performance Goal: {'✅ MET' if avg_time_per_case <= target_time else '❌ NOT MET'}")

def save_test_results(results: Dict, filename: str = "test_results.json"):
    """Save test results to JSON file"""
    # Convert dataclasses to dicts for JSON serialization
    serializable_results = {}
    
    for domain, domain_results in results.items():
        serializable_results[domain] = []
        for result in domain_results:
            serializable_result = {
                'case_name': result['case_name'],
                'enhanced_result': {
                    'entity_count': len(result['enhanced_result']['entities']),
                    'processing_time': result['enhanced_result']['processing_time'],
                    'stats': result['enhanced_result']['stats']
                },
                'fallback_result': {
                    'entity_count': len(result['fallback_result']['enhanced_entities']),
                    'processing_time': result['fallback_result']['processing_time'],
                    'coverage_improvement': result['fallback_result']['coverage_improvement']
                },
                'integrated_result': {
                    'entity_count': len(result['integrated_result']['entities']),
                    'processing_time': result['integrated_result']['processing_time'],
                    'coverage_stats': result['integrated_result']['coverage_stats']
                },
                'enhanced_coverage': result['enhanced_coverage'],
                'integrated_coverage': result['integrated_coverage'],
                'quality_assessment': result['quality_assessment']
            }
            serializable_results[domain].append(serializable_result)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\n💾 Test results saved to {filename}")

if __name__ == "__main__":
    # Run comprehensive tests
    results = run_comprehensive_test()
    
    # Generate report
    generate_test_report(results)
    
    # Save results
    save_test_results(results, "enhanced_entity_test_results.json")
    
    print(f"\n🎉 Enhanced Entity Extraction System Testing Complete!")
    print(f"   Results saved to: enhanced_entity_test_results.json")