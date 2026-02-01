"""
Enhanced Entity Extraction Module

Improves entity recognition accuracy through:
1. Multi-stage fallback classification
2. Context-aware entity linking
3. Expanded entity coverage
4. Better normalization and disambiguation

Usage:
    from enhanced_entity_extractor import EnhancedEntityExtractor
    
    extractor = EnhancedEntityExtractor(domain="construction_science")
    entities = extractor.extract_entities(text, title=title)
    normalized_entities = extractor.normalize_entities(entities)
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)
@dataclass
class Entity:
    entity_type: str
    entity_name: str
    entity_variant: Optional[str]
    confidence: float
    source: str
    context_window: Optional[str] = None
    position: Optional[Tuple[int, int]] = None

class EnhancedEntityExtractor:
    """Enhanced entity extraction with multi-stage fallback and context awareness"""
    
    def __init__(self, domain: str = "methods_tooling"):
        self.domain = domain
        self._seeds = None
        self._normalization_map = None
        self._context_patterns = None
        self._abbreviation_patterns = None
        self._domain_config = None  # Lazy loaded via property
        
    def _load_seeds(self) -> Dict:
        """Load all seed files with enhanced error handling"""
        seeds = {}
        
        # Load JSON seeds
        seeds_dir = Path("seeds")
        if seeds_dir.exists():
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
    
    def _load_normalization_map(self) -> Dict:
        """Load entity normalization mappings"""
        norm_file = Path("seeds/normalization.json")
        if norm_file.exists():
            try:
                return json.loads(norm_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load normalization map: {e}")
        return {}
    
    def _load_context_patterns(self) -> Dict:
        """Load context patterns for entity disambiguation"""
        return {
            'construction': {
                'material_context': [
                    r'(?:material|construction|building|structural).*?(?:test|analysis|performance)',
                    r'(?:concrete|steel|wood|glass).*?(?:strength|durability|performance)',
                    r'(?:material|component).*?(?:failure|degradation|corrosion)'
                ],
                'system_context': [
                    r'(?:system|assembly|component).*?(?:performance|failure|analysis)',
                    r'(?:wall|roof|foundation).*?(?:design|analysis|performance)'
                ],
                'environment_context': [
                    r'(?:environment|condition|exposure).*?(?:effect|impact|performance)',
                    r'(?:temperature|humidity|corrosive).*?(?:effect|impact|performance)'
                ]
            },
            'biomedical': {
                'compound_context': [
                    r'(?:compound|drug|molecule).*?(?:activity|efficacy|potency)',
                    r'(?:inhibit|activate|bind).*?(?:target|receptor|enzyme)'
                ],
                'target_context': [
                    r'(?:target|receptor|enzyme).*?(?:expression|activity|function)',
                    r'(?:protein|gene).*?(?:expression|mutation|variant)'
                ],
                'assay_context': [
                    r'(?:assay|test|analysis).*?(?:result|measurement|data)',
                    r'(?:ic50|ec50|kd|ki).*?(?:value|measurement|result)'
                ]
            }
        }
    
    def _load_abbreviation_patterns(self) -> Dict:
        """Load common abbreviation patterns"""
        return {
            'construction': {
                'concrete': ['concrete', 'conc', 'cocrete'],
                'steel': ['steel', 'stl'],
                'wood': ['wood', 'timber', 'lumber'],
                'glass': ['glass', 'glz'],
                'brick': ['brick', 'brk'],
                'masonry': ['masonry', 'msonry'],
                'foundation': ['foundation', 'found', 'fdn'],
                'beam': ['beam', 'bm'],
                'column': ['column', 'col', 'clm'],
                'wall': ['wall', 'wl'],
                'roof': ['roof', 'rf'],
                'floor': ['floor', 'flr'],
                'insulation': ['insulation', 'insul', 'ins'],
                'moisture': ['moisture', 'moist', 'mstr'],
                'corrosion': ['corrosion', 'corrode', 'corr'],
                'durability': ['durability', 'durable', 'dur'],
                'strength': ['strength', 'str', 'stren'],
                'performance': ['performance', 'perf', 'prf'],
                'failure': ['failure', 'fail', 'fl'],
                'crack': ['crack', 'crk'],
                'deflection': ['deflection', 'defl', 'def'],
                'settlement': ['settlement', 'settl', 'sett'],
                'load': ['load', 'ld'],
                'stress': ['stress', 'strs'],
                'strain': ['strain', 'strn'],
                'temperature': ['temperature', 'temp', 'tmp'],
                'humidity': ['humidity', 'humid', 'hum'],
                'fire': ['fire', 'flame', 'fr'],
                'water': ['water', 'wtr', 'h2o'],
                'vapor': ['vapor', 'vpr'],
                'air': ['air'],
                'wind': ['wind', 'wnd'],
                'seismic': ['seismic', 'earthquake', 'eq'],                'snow': ['snow', 'snw'],
                'ice': ['ice', 'ic'],
                'frost': ['frost', 'frst'],
                'freeze': ['freeze', 'frz'],
                'thaw': ['thaw', 'thw'],
                'thermal': ['thermal', 'therm', 'th'],
                'acoustic': ['acoustic', 'sound', 'ac'],
                'structural': ['structural', 'struct', 'str'],
                'mechanical': ['mechanical', 'mech', 'mc'],
                'chemical': ['chemical', 'chem', 'ch'],
                'physical': ['physical', 'phys', 'ph'],
                'environmental': ['environmental', 'env', 'envr'],
                'building': ['building', 'bldg', 'bld'],
                'construction': ['construction', 'const', 'cnst'],
                'design': ['design', 'des', 'ds'],
                'analysis': ['analysis', 'anal', 'anl'],
                'test': ['test', 'tst'],
                'method': ['method', 'meth', 'mth'],
                'procedure': ['procedure', 'proc', 'prc'],
                'standard': ['standard', 'std', 'stnd'],
                'code': ['code', 'cd'],
                'specification': ['specification', 'spec', 'spc'],
                'requirement': ['requirement', 'req', 'rqr'],
                'guideline': ['guideline', 'guid', 'gdl'],
                'practice': ['practice', 'prac', 'pr'],
                'technique': ['technique', 'tech', 'tch'],
                'approach': ['approach', 'app', 'apr'],
                'strategy': ['strategy', 'strat', 'stg'],
                'solution': ['solution', 'sol', 'sl'],
                'system': ['system', 'sys', 'sys'],
                'component': ['component', 'comp', 'cmp'],
                'element': ['element', 'elem', 'elm'],
                'member': ['member', 'mem', 'mbr'],
                'connection': ['connection', 'conn', 'cn'],
                'joint': ['joint', 'jnt'],
                'anchor': ['anchor', 'anch', 'anc'],
                'fastener': ['fastener', 'fast', 'fst'],
                'bolt': ['bolt', 'blt'],
                'screw': ['screw', 'scr'],
                'nail': ['nail', 'nl'],
                'weld': ['weld', 'wld'],
                'adhesive': ['adhesive', 'adhs', 'adh'],
                'sealant': ['sealant', 'seal', 'sl'],
                'coating': ['coating', 'coat', 'ct'],
                'paint': ['paint', 'pnt'],
                'finish': ['finish', 'fnsh', 'fn'],
                'surface': ['surface', 'surf', 'sf'],
                'interface': ['interface', 'intf', 'if'],
                'boundary': ['boundary', 'bnd', 'bd'],
                'transition': ['transition', 'trans', 'tr'],
                'junction': ['junction', 'jnc', 'jct'],
                'intersection': ['intersection', 'intr', 'ix'],
                'penetration': ['penetration', 'pen', 'pn'],
                'opening': ['opening', 'opn', 'op'],
                'void': ['void', 'vd'],
                'cavity': ['cavity', 'cav', 'cv'],
                'gap': ['gap', 'gp'],
                'fissure': ['fissure', 'fis', 'fs'],
                'fracture': ['fracture', 'frac', 'fr'],
                'split': ['split', 'splt', 'sp'],
                'tear': ['tear', 'tr'],
                'rip': ['rip', 'rp'],
                'break': ['break', 'brk'],
                'damage': ['damage', 'dm', 'dg'],
                'deterioration': ['deterioration', 'deter', 'dt'],
                'degradation': ['degradation', 'degrad', 'dg'],
                'decay': ['decay', 'dcy', 'dc'],
                'rot': ['rot', 'rt'],
                'oxidation': ['oxidation', 'oxid', 'ox'],
                'weathering': ['weathering', 'weather', 'wth'],
                'erosion': ['erosion', 'eros', 'er'],
                'wear': ['wear', 'wr'],
                'fatigue': ['fatigue', 'fat', 'ft'],
                'creep': ['creep', 'crp'],
                'shrinkage': ['shrinkage', 'shrink', 'shk'],
                'expansion': ['expansion', 'expand', 'exp'],
                'contraction': ['contraction', 'contract', 'cont'],
                'movement': ['movement', 'move', 'mv'],
                'displacement': ['displacement', 'displace', 'dsp'],
                'deformation': ['deformation', 'deform', 'dfm'],
                'distortion': ['distortion', 'distort', 'dstr'],
                'buckling': ['buckling', 'buckle', 'bkl'],
                'sag': ['sag', 'sg'],
                'bow': ['bow', 'bw'],
                'twist': ['twist', 'twt', 'tw'],
                'warp': ['warp', 'wrp'],
                'camber': ['camber', 'cmb'],
                'slope': ['slope', 'slp'],
                'grade': ['grade', 'grd'],
                'pitch': ['pitch', 'ptch', 'pt'],
                'angle': ['angle', 'ang', 'ag'],
                'orientation': ['orientation', 'orient', 'ort'],
                'alignment': ['alignment', 'align', 'aln'],
                'position': ['position', 'pos', 'ps'],
                'location': ['location', 'loc', 'lc'],
                'placement': ['placement', 'place', 'plc'],
                'installation': ['installation', 'install', 'inst'],
                'erection': ['erection', 'erect', 'er'],
                'assembly': ['assembly', 'assem', 'asm'],
                'fabrication': ['fabrication', 'fabric', 'fab'],
                'manufacturing': ['manufacturing', 'manufact', 'mfg'],
                'production': ['production', 'product', 'prod']
            }
        }
    
    @property
    def seeds(self) -> Dict:
        """Lazy load seeds on first access"""
        if self._seeds is None:
            self._seeds = self._load_seeds()
        return self._seeds
    
    @property
    def normalization_map(self) -> Dict:
        """Lazy load normalization map on first access"""
        if self._normalization_map is None:
            self._normalization_map = self._load_normalization_map()
        return self._normalization_map
    
    @property
    def context_patterns(self) -> Dict:
        """Lazy load context patterns on first access"""
        if self._context_patterns is None:
            self._context_patterns = self._load_context_patterns()
        return self._context_patterns
    
    @property
    def abbreviation_patterns(self) -> Dict:
        """Lazy load abbreviation patterns on first access"""
        if self._abbreviation_patterns is None:
            self._abbreviation_patterns = self._load_abbreviation_patterns()
        return self._abbreviation_patterns
    
    @property
    def domain_config(self) -> Dict:
        """Get domain-specific configuration"""
        if self._domain_config is None:
            if self.domain == "construction_science":
                self._domain_config = {
                    'entity_types': ['materials', 'systems', 'environments', 'failure_modes', 'test_methods', 'codes', 'hazards'],
                    'context_types': ['material_context', 'system_context', 'environment_context'],
                    'abbreviation_map': self.abbreviation_patterns.get('construction', {})
                }
            else:
                self._domain_config = {
                    'entity_types': ['compound', 'target', 'model', 'assay', 'pathway', 'indication', 'stem_cell', 'peptide_class'],
                    'context_types': ['compound_context', 'target_context', 'assay_context'],
                    'abbreviation_map': {}
                }
        return self._domain_config
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for entity matching"""
        # Normalize Unicode (NFKD) and remove combining diacritics only
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        # Normalize hyphens
        text = re.sub(r'[-–—]', '-', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        return text.lower()
    def _is_valid_entity_for_domain(self, entity_name: str, entity_type: str) -> bool:
        """Validate if entity is appropriate for the current domain"""
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
        
        entity_lower = entity_name.lower().strip()
        
        # Check against junk patterns
        for pattern in junk_patterns:
            if re.match(pattern, entity_lower):
                return False
        
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
        
        elif self.domain in ["methods_tooling", "biohacking_longevity"]:
            # Filter out construction-specific terms that might leak through
            construction_terms = ['concrete', 'steel', 'wood', 'glass', 'brick', 'masonry', 'foundation', 'beam', 'column']
            if any(term in entity_lower for term in construction_terms):
                return False
        
        return True
    
    def _extract_ontology_entities(self, text: str) -> List[Entity]:
        """Extract entities using ontology seeds"""
        entities = []
        text_lower = self._normalize_text(text)
        
        if 'ontology' not in self.seeds or self.domain not in self.seeds['ontology']:
            return entities
        
        ontology = self.seeds['ontology'][self.domain]
        
        for entity_type in self.domain_config['entity_types']:
            if entity_type not in ontology:
                continue
                
            for entity_name in ontology[entity_type]:
                # Check exact match
                if entity_name.lower() in text_lower:
                    # Apply domain-specific filtering
                    if self._is_valid_entity_for_domain(entity_name, entity_type):
                        entities.append(Entity(
                            entity_type=entity_type,
                            entity_name=entity_name.upper(),
                            entity_variant=None,
                            confidence=0.8,
                            source="ontology_exact"
                        ))
                
                # Check abbreviation variants
                if entity_name.lower() in self.domain_config['abbreviation_map']:
                    for variant in self.domain_config['abbreviation_map'][entity_name.lower()]:
                        if variant.lower() in text_lower and variant.lower() != entity_name.lower():
                            # Apply domain-specific filtering to variants too
                            if self._is_valid_entity_for_domain(variant, entity_type):
                                entities.append(Entity(
                                    entity_type=entity_type,
                                    entity_name=entity_name.upper(),
                                    entity_variant=variant.upper(),
                                    confidence=0.6,
                                    source="ontology_abbreviation"
                                ))
        
        return entities
    
    def _extract_json_entities(self, text: str) -> List[Entity]:
        """Extract entities using JSON seeds"""
        entities = []
        text_lower = self._normalize_text(text)
        
        # Only extract JSON entities for non-construction domains
        if self.domain == "construction_science":
            return entities
        
        # Extract assays
        if 'assays' in self.seeds:
            for assay in self.seeds['assays'].get('assays', []):
                name = assay.get('name', '')
                if name.lower() in text_lower:
                    # Apply domain-specific filtering
                    if self._is_valid_entity_for_domain(name, "assay"):
                        entities.append(Entity(
                            entity_type="assay",
                            entity_name=name,
                            entity_variant="assay",
                            confidence=0.85,
                            source="json_assay"
                        ))
            
            for metric in self.seeds['assays'].get('metrics', []):
                if metric.lower() in text_lower:
                    # Apply domain-specific filtering
                    if self._is_valid_entity_for_domain(metric, "assay"):
                        entities.append(Entity(
                            entity_type="assay",
                            entity_name=metric,
                            entity_variant="metric",
                            confidence=0.70,
                            source="json_metric"
                        ))
        
        # Extract pathways
        if 'pathways' in self.seeds:
            for pathway in self.seeds['pathways'].get('pathways', []):
                if pathway.lower() in text_lower:
                    # Apply domain-specific filtering
                    if self._is_valid_entity_for_domain(pathway, "pathway"):
                        entities.append(Entity(
                            entity_type="pathway",
                            entity_name=pathway,
                            entity_variant="pathway",
                            confidence=0.80,
                            source="json_pathway"
                        ))
        
        # Extract indications
        if 'indications' in self.seeds:
            for indication in self.seeds['indications'].get('indications', []):
                if isinstance(indication, dict):
                    indication_name = indication.get('name', '')
                else:
                    indication_name = str(indication)
                if indication_name.lower() in text_lower:
                    # Apply domain-specific filtering
                    if self._is_valid_entity_for_domain(indication_name, "indication"):
                        entities.append(Entity(
                            entity_type="indication",
                            entity_name=indication_name,
                            entity_variant="disease",
                            confidence=0.75,
                            source="json_indication"
                        ))
        
        return entities
    
    def _extract_context_entities(self, text: str) -> List[Entity]:
        """Extract entities using context patterns"""
        entities = []
        text_lower = self._normalize_text(text)
        
        context_types = self.domain_config.get('context_types', [])
        
        # Map domain to context pattern key
        domain_key = 'construction' if self.domain == 'construction_science' else 'biomedical'
        
        for context_type in context_types:
            if context_type in self.context_patterns.get(domain_key, {}):
                patterns = self.context_patterns[domain_key][context_type]
                for pattern in patterns:
                    if re.search(pattern, text_lower):
                        # Extract potential entities from context
                        potential_entities = self._extract_entities_from_context(text_lower, context_type)
                        for entity in potential_entities:
                            entities.append(Entity(
                                entity_type=entity['type'],
                                entity_name=entity['name'],
                                entity_variant=entity.get('variant'),
                                confidence=0.5,
                                source="context_pattern"
                            ))
        
        return entities
    
    def _extract_entities_from_context(self, text: str, context_type: str) -> List[Dict]:
        """Extract potential entities from context patterns"""
        entities = []
        
        # Simple heuristics for entity extraction from context
        if context_type == 'material_context':
            # Look for material-related words
            material_patterns = [
                r'\b(concrete|steel|wood|glass|brick|masonry)\b',
                r'\b(strength|durability|performance)\b'
            ]
            for pattern in material_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    entities.append({'type': 'material', 'name': match.upper()})
        
        elif context_type == 'system_context':
            # Look for system-related words
            system_patterns = [
                r'\b(wall|roof|foundation|beam|column)\b',
                r'\b(system|assembly|component)\b'
            ]
            for pattern in system_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    entities.append({'type': 'system', 'name': match.upper()})
        
        elif context_type == 'environment_context':
            # Look for environment-related words
            environment_patterns = [
                r'\b(temperature|humidity|corrosive|exposure)\b',
                r'\b(environment|condition)\b'
            ]
            for pattern in environment_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    entities.append({'type': 'environment', 'name': match.upper()})
        
        return entities
    
    def _extract_sequence_entities(self, text: str) -> List[Entity]:
        """Extract peptide sequences using enhanced patterns"""
        entities = []
        
        # Enhanced sequence patterns
        sequence_patterns = [
            r'sequence[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
            r'seq[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
            r'peptide[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
            r'residues?\s+\d+[-–]\d+[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
            r'[Nn]-terminus[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
            r'[Cc]-terminus[:\s]+([ACDEFGHIKLMNPQRSTVWY]{8,100})',
            r'\(([ACDEFGHIKLMNPQRSTVWY]{8,100})\)',
            r'\[([ACDEFGHIKLMNPQRSTVWY]{8,100})\]',
        ]
        
        for pattern in sequence_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                seq = match.group(1).upper()
                if self._is_valid_sequence(seq, text):
                    entities.append(Entity(
                        entity_type="peptide",
                        entity_name=seq,
                        entity_variant="sequence",
                        confidence=0.9,
                        source="sequence_pattern"
                    ))
        
        return entities
    
    def _is_valid_sequence(self, seq: str, context: str) -> bool:
        """Validate if sequence is likely a real peptide"""
        # Length check
        if len(seq) < 8 or len(seq) > 100:
            return False
        
        # Character check
        valid_chars = set('ACDEFGHIKLMNPQRSTVWY')
        if not all(c in valid_chars for c in seq):
            return False
        
        # Complexity check
        if len(set(seq)) < 4:
            return False
        
        # Context check (avoid split words)
        context_upper = context.upper()
        seq_upper = seq.upper()
        idx = context_upper.find(seq_upper)
        
        if idx != -1:
            before_idx = idx - 1
            after_idx = idx + len(seq_upper)
            
            if before_idx >= 0 and context[before_idx].isalpha():
                return False
            if after_idx < len(context) and context[after_idx].isalpha():
                return False
        
        return True
    
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Deduplicate entities by type and name, keeping highest confidence"""
        seen = set()
        deduplicated = []
        
        # Sort by confidence descending (non-mutating)
        sorted_entities = sorted(entities, key=lambda x: x.confidence, reverse=True)

        for entity in sorted_entities:
            key = (entity.entity_type, entity.entity_name, entity.entity_variant)
            if key not in seen:
                seen.add(key)
                deduplicated.append(entity)
        
        return deduplicated
    
    def _add_context_windows(self, entities: List[Entity], text: str) -> List[Entity]:
        """Add context windows to entities"""
        for entity in entities:
            if entity.entity_name.lower() in text.lower():
                start = text.lower().find(entity.entity_name.lower())
                end = start + len(entity.entity_name)
                
                # Add context window (50 chars before and after)
                context_start = max(0, start - 50)
                context_end = min(len(text), end + 50)
                context_window = text[context_start:context_end]
                
                entity.context_window = context_window
                entity.position = (start, end)
        
        return entities
    
    def extract_entities(self, text: str, title: str = "") -> List[Entity]:
        """
        Extract entities using multi-stage fallback approach
        
        Stage 1: Ontology-based extraction (highest confidence)
        Stage 2: JSON seed extraction
        Stage 3: Context pattern extraction
        Stage 4: Sequence extraction (for peptides)
        """
        all_entities = []
        
        # Stage 1: Ontology entities
        ontology_entities = self._extract_ontology_entities(text)
        all_entities.extend(ontology_entities)
        
        # Stage 2: JSON entities
        json_entities = self._extract_json_entities(text)
        all_entities.extend(json_entities)
        
        # Stage 3: Context entities
        context_entities = self._extract_context_entities(text)
        all_entities.extend(context_entities)
        
        # Stage 4: Sequence entities
        sequence_entities = self._extract_sequence_entities(text)
        all_entities.extend(sequence_entities)
        
        # Deduplicate and add context
        entities = self._deduplicate_entities(all_entities)
        entities = self._add_context_windows(entities, text)
        
        return entities
    
    def normalize_entities(self, entities: List[Entity]) -> List[Entity]:
        """Normalize entity names using normalization map"""
        normalized = []
        
        for entity in entities:
            normalized_name = self._normalize_entity_name(entity.entity_type, entity.entity_name)
            normalized_entity = Entity(
                entity_type=entity.entity_type,
                entity_name=normalized_name,
                entity_variant=entity.entity_variant,
                confidence=entity.confidence,
                source=entity.source,
                context_window=entity.context_window,
                position=entity.position
            )
            normalized.append(normalized_entity)
        
        return normalized
    
    def _normalize_entity_name(self, entity_type: str, entity_name: str) -> str:
        """Normalize entity name using normalization map"""
        if entity_type not in self.normalization_map:
            return entity_name
        
        for canonical, variants in self.normalization_map[entity_type].items():
            for variant in variants:
                if entity_name.lower() == variant.lower():
                    return canonical
        
        return entity_name
    
    def get_entity_coverage_stats(self, entities: List[Entity]) -> Dict:
        """Get entity coverage statistics"""
        if not entities:
            return {
                'total_entities': 0,
                'unique_types': 0,
                'coverage_by_type': {},
                'avg_confidence': 0.0
            }
        
        entity_types = [e.entity_type for e in entities]
        unique_types = set(entity_types)
        coverage_by_type = {t: entity_types.count(t) for t in unique_types}
        avg_confidence = sum(e.confidence for e in entities) / len(entities)
        
        return {
            'total_entities': len(entities),
            'unique_types': len(unique_types),
            'coverage_by_type': coverage_by_type,
            'avg_confidence': round(avg_confidence, 2)
        }

# Backward compatibility function
def extract_entities(text: str, seeds: Dict, title: str = "") -> List[Dict]:
    """
    Backward compatible entity extraction function
    
    Returns list of entity dicts for compatibility with existing code
    """
    if seeds is not None and isinstance(seeds, dict):
        domain = seeds.get('domain', 'methods_tooling')
        extractor = EnhancedEntityExtractor(domain=domain)
    elif seeds is not None and isinstance(seeds, str):
        extractor = EnhancedEntityExtractor(domain=seeds)
    else:
        extractor = EnhancedEntityExtractor()
    entities = extractor.extract_entities(text, title)
    normalized = extractor.normalize_entities(entities)
    # Convert to dict format for compatibility
    return [asdict(entity) for entity in normalized]
# Example usage and testing
if __name__ == "__main__":
    # Test with construction science
    print("Testing Enhanced Entity Extractor")
    print("=" * 50)
    
    extractor = EnhancedEntityExtractor(domain="construction_science")
    
    test_text = """
    The concrete beam showed significant cracking after 5 years of exposure to 
    corrosive environments. The steel reinforcement experienced severe corrosion 
    leading to structural failure. Temperature variations caused thermal expansion 
    and contraction, resulting in additional stress on the masonry walls.
    """
    
    entities = extractor.extract_entities(test_text)
    normalized = extractor.normalize_entities(entities)
    stats = extractor.get_entity_coverage_stats(normalized)
    
    print(f"Original entities: {len(entities)}")
    print(f"Normalized entities: {len(normalized)}")
    print(f"Coverage stats: {stats}")
    
    print("\nExtracted entities:")
    for entity in normalized:
        print(f"  {entity.entity_type}: {entity.entity_name} (confidence: {entity.confidence})")
    
    # Test with biomedical domain
    print("\n" + "=" * 50)
    print("Testing with biomedical domain")
    
    bio_extractor = EnhancedEntityExtractor(domain="methods_tooling")
    bio_text = """
    The compound showed potent activity against the target protein with an IC50 of 10nM.
    The assay results demonstrated significant inhibition of the pathway in vitro.
    """
    
    bio_entities = bio_extractor.extract_entities(bio_text)
    bio_normalized = bio_extractor.normalize_entities(bio_entities)
    
    print(f"Biomedical entities: {len(bio_normalized)}")
    for entity in bio_normalized:
        print(f"  {entity.entity_type}: {entity.entity_name} (confidence: {entity.confidence})")
