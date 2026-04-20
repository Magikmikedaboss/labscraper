"""
Quantitative and relationship extraction logic for PDF scraping pipeline.
Includes: extract_quantitative_data, QUANTITATIVE_PATTERNS, extract_relationships, RELATIONSHIP_PATTERNS.
"""
"""
Quantitative and relationship extraction logic for PDF scraping pipeline.
Includes: extract_quantitative_data, QUANTITATIVE_PATTERNS, extract_relationships, RELATIONSHIP_PATTERNS.
"""
import re
import logging

QUANTITATIVE_PATTERNS = [
    (re.compile(r'ic50.*?(\d+\.?\d*)\s*(nm|[\u00B5\u03BC]m|mm)', re.I), 'ic50'),
    (re.compile(r'ec50.*?(\d+\.?\d*)\s*(nm|[\u00B5\u03BC]m|mm)', re.I), 'ec50'),
    (re.compile(r'kd.*?(\d+\.?\d*)\s*(nm|[\u00B5\u03BC]m|mm)', re.I), 'kd'),
    (re.compile(r'ki.*?(\d+\.?\d*)\s*(nm|[\u00B5\u03BC]m|mm)', re.I), 'ki'),
    (re.compile(r'half[- ]?life.*?(\d+\.?\d*)\s*(min|hour|day|hr|h)', re.I), 'half_life'),
    (re.compile(r'stability.*?(\d+\.?\d*)\s*(%|percent)', re.I), 'stability_percent'),
    (re.compile(r't1/2.*?(\d+\.?\d*)\s*(min|hour|day|hr|h)', re.I), 'half_life'),
]

def extract_quantitative_data(sentence: str) -> list[dict]:
    """Extract numerical measurements from sentence"""
    measurements = []
    s_l = sentence.lower()
    for pattern, mtype in QUANTITATIVE_PATTERNS:
        matches = pattern.finditer(s_l)
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
            except (ValueError, IndexError) as e:
                logging.warning(
                    "extract_quantitative_data: Failed to parse match '%s' with pattern '%s': %s",
                    m.group(0), pattern.pattern, e
                )
                continue
    return measurements

_ENTITY_PATTERN = r'([\w-]+(?:\s+[\w-]+)*)'
RELATIONSHIP_PATTERNS = [
    (re.compile(rf'{_ENTITY_PATTERN}\s+(?:was|is|showed)\s+more\s+stable\s+than\s+{_ENTITY_PATTERN}', re.I), 'more_stable_than'),
    (re.compile(rf'{_ENTITY_PATTERN}\s+(?:was|is|showed)\s+more\s+potent\s+than\s+{_ENTITY_PATTERN}', re.I), 'more_potent_than'),
    (re.compile(rf'{_ENTITY_PATTERN}\s+(?:was|is)\s+less\s+toxic\s+than\s+{_ENTITY_PATTERN}', re.I), 'less_toxic_than'),
    (re.compile(rf'{_ENTITY_PATTERN}\s+(?:is|was)\s+(?:a|an)\s+analog\s+of\s+{_ENTITY_PATTERN}', re.I), 'analog_of'),
    (re.compile(rf'{_ENTITY_PATTERN}\s+(?:is|was)\s+(?:a|an)\s+derivative\s+of\s+{_ENTITY_PATTERN}', re.I), 'derivative_of'),
]

def extract_relationships(sentence: str, entities: list[dict]) -> list[dict]:
    """Extract relationships between entities"""
    relationships = []
    s_l = sentence.lower()
    valid_entities = []
    for e in entities:
        if 'entity_name' in e and e['entity_name']:
            valid_entities.append(e)
        else:
            logging.warning("extract_relationships: Skipping entity without 'entity_name': %r", e)
    # Map lowercased entity_name to original entity_name
    entity_name_map = {e['entity_name'].lower(): e['entity_name'] for e in valid_entities}
    entity_names = set(entity_name_map.keys())
    for pattern, rtype in RELATIONSHIP_PATTERNS:
        for m in pattern.finditer(s_l):
            ent1, ent2 = m.group(1), m.group(2)
            relationships.append({
                'relationship_type': rtype,
                'entity_1': ent1,
                'entity_2': ent2,
                'context': m.group(0)
            })
    return relationships
