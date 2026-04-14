"""
Quantitative and relationship extraction logic for PDF scraping pipeline.
Includes: extract_quantitative_data, QUANTITATIVE_PATTERNS, extract_relationships, RELATIONSHIP_PATTERNS.
"""
import re

QUANTITATIVE_PATTERNS = [
    (r'ic50.*?(\d+\.?\d*)\s*(nm|[\u00B5\u03BC]m|mm)', 'ic50'),
    (r'ec50.*?(\d+\.?\d*)\s*(nm|[\u00B5\u03BC]m|mm)', 'ec50'),
    (r'kd.*?(\d+\.?\d*)\s*(nm|[\u00B5\u03BC]m|mm)', 'kd'),
    (r'ki.*?(\d+\.?\d*)\s*(nm|[\u00B5\u03BC]m|mm)', 'ki'),
    (r'half[- ]?life.*?(\d+\.?\d*)\s*(min|hour|day|hr|h)', 'half_life'),
    (r'stability.*?(\d+\.?\d*)\s*(%|percent)', 'stability_percent'),
    (r't1/2.*?(\d+\.?\d*)\s*(min|hour|day|hr|h)', 'half_life'),
]

def extract_quantitative_data(sentence: str) -> list[dict]:
    """Extract numerical measurements from sentence"""
    measurements = []
    s_l = sentence.lower()
    for pattern, mtype in QUANTITATIVE_PATTERNS:
        matches = re.finditer(pattern, s_l)
        for m in matches:
            try:
                value = float(m.group(1))
                unit = m.group(2)
                measurements.append({
                    'measurement_type': mtype,
                    'value': value,
                    'unit': unit,
                    'context': m.group(0)
                })
            except (ValueError, IndexError):
                continue
    return measurements

RELATIONSHIP_PATTERNS = [
    (r'(\w+)\s+(?:was|is|showed)\s+more\s+stable\s+than\s+(\w+)', 'more_stable_than'),
    (r'(\w+)\s+(?:was|is|showed)\s+more\s+potent\s+than\s+(\w+)', 'more_potent_than'),
    (r'(\w+)\s+(?:was|is)\s+less\s+toxic\s+than\s+(\w+)', 'less_toxic_than'),
    (r'(\w+)\s+(?:is|was)\s+(?:a|an)\s+analog\s+of\s+(\w+)', 'analog_of'),
    (r'(\w+)\s+(?:is|was)\s+(?:a|an)\s+derivative\s+of\s+(\w+)', 'derivative_of'),
]

def extract_relationships(sentence: str, entities: list[dict]) -> list[dict]:
    """Extract relationships between entities"""
    relationships = []
    s_l = sentence.lower()
    entity_names = {e['entity_name'].lower() for e in entities}
    for pattern, rel_type in RELATIONSHIP_PATTERNS:
        matches = re.finditer(pattern, s_l)
        for m in matches:
            entity1 = m.group(1).upper()
            entity2 = m.group(2).upper()
            if entity1.lower() in entity_names and entity2.lower() in entity_names:
                relationships.append({
                    'entity_1': entity1,
                    'entity_2': entity2,
                    'relationship_type': rel_type,
                    'confidence': 'med'
                })
    return relationships
