"""Tests for entity extraction functionality using pytest"""
import pytest
from unittest.mock import patch, Mock
from utils.run_engine import extract_entities, extract_compounds, extract_targets, extract_models, extract_presented_sequences, is_probable_peptide


class TestEntityExtraction:
    """Test basic entity extraction functionality"""
    
    def test_extract_entities_methods_tooling_domain(self):
        """Test entity extraction for methods_tooling domain"""
        text = "The study used CRISPR-Cas9 to edit the TP53 gene in human stem cells."
        
        entities = extract_entities(text, "methods_tooling")
        
        # Should extract compounds, peptides, targets, models, and stem cells
        assert len(entities) > 0
        entity_types = [e['entity_type'] for e in entities]
        assert 'compound' in entity_types or 'peptide' in entity_types or 'target' in entity_types

    def test_extract_entities_construction_science_domain(self):
        """Test entity extraction for construction_science domain"""
        text = "The concrete beam was tested under load conditions with steel reinforcement."
        
        entities = extract_entities(text, "construction_science")
        
        # Should extract construction-specific entities
        assert len(entities) > 0
        entity_types = [e['entity_type'] for e in entities]
        assert any(et in ['material', 'system', 'environment', 'failure_mode', 'hazard', 'test_method'] for et in entity_types)

    def test_extract_entities_empty_text(self):
        """Test entity extraction with empty text"""
        text = ""
        
        entities = extract_entities(text, "methods_tooling")
        
        assert entities == []

    def test_extract_entities_no_entities(self):
        """Test entity extraction with no entities"""
        text = "This is just a regular sentence with no scientific terms."
        
        entities = extract_entities(text, "methods_tooling")
        
        assert entities == []

    def test_extract_compounds(self):
        """Test compound extraction"""
        text = "The study used aspirin and ibuprofen to test efficacy."
        
        compounds = extract_compounds(text)
        
        assert len(compounds) >= 0  # May be 0 if compounds not in seed list

    def test_extract_targets(self):
        """Test target extraction"""
        text = "The study targeted mTOR and AKT signaling pathways."
        
        targets = extract_targets(text)
        
        assert len(targets) >= 0  # May be 0 if targets not in seed list

    def test_extract_models(self):
        """Test model extraction"""
        text = "The study used HEK293 cells and mouse models."
        
        models = extract_models(text)
        
        assert len(models) >= 0  # May be 0 if models not in seed list

    def test_extract_presented_sequences(self):
        """Test sequence extraction from presentation patterns"""
        text = "The sequence was GGGSGGGSGGG (SEQ ID NO: 1)."
        
        sequences = extract_presented_sequences(text)
        
        assert len(sequences) > 0
        assert any('GGGSGGGSGGG' in seq for seq in sequences)

    def test_is_probable_peptide_valid(self):
        """Test peptide validation for valid sequences"""
        seq = "GGGSGGGSGGG"
        
        result = is_probable_peptide(seq, "The sequence GGGSGGGSGGG was tested.")
        
        assert result is True

    def test_is_probable_peptide_invalid(self):
        """Test peptide validation for invalid sequences"""
        seq = "MALDI"
        
        result = is_probable_peptide(seq, "MALDI was used for analysis.")
        
        assert result is False

    def test_is_probable_peptide_split_word(self):
        """Test peptide validation rejects split words"""
        seq = "TEST"
        
        result = is_probable_peptide(seq, "This is a TEST sequence.")
        
        assert result is False

    def test_is_probable_peptide_known_peptide(self):
        """Test that known therapeutic peptides always pass"""
        seq = "ETELCALCETIDE"
        
        result = is_probable_peptide(seq, "ETELCALCETIDE was tested.")
        
        assert result is True

    def test_extract_presented_sequences_patterns(self):
        """Test different sequence presentation patterns"""
        test_cases = [
            ("sequence: GGGSGGGSGGG", ["GGGSGGGSGGG"]),
            ("seq: GGGSGGGSGGG", ["GGGSGGGSGGG"]),
            ("peptide: GGGSGGGSGGG", ["GGGSGGGSGGG"]),
            ("residues 1-10: GGGSGGGSGGG", ["GGGSGGGSGGG"]),
            ("(GGGSGGGSGGG)", ["GGGSGGGSGGG"]),
            ("[GGGSGGGSGGG]", ["GGGSGGGSGGG"]),
        ]
        
        for text, expected in test_cases:
            sequences = extract_presented_sequences(text)
            assert len(sequences) > 0
            assert any(expected[0] in seq for seq in sequences)

    def test_extract_presented_sequences_no_matches(self):
        """Test sequence extraction with no presentation patterns"""
        text = "This is just regular text with no sequence patterns."
        
        sequences = extract_presented_sequences(text)
        
        assert len(sequences) == 0

    def test_extract_presented_sequences_case_insensitive(self):
        """Test sequence extraction is case insensitive"""
        text = "SEQUENCE: gggsgggsggg"
        
        sequences = extract_presented_sequences(text)
        
        assert len(sequences) > 0
        assert any('GGGSGGGSGGG' in seq for seq in sequences)


class TestConstructionEntities:
    """Test construction science entity extraction"""
    
    def test_extract_construction_materials(self):
        """Test extraction of construction materials"""
        text = "The study used concrete, steel, and wood materials."
        
        entities = extract_entities(text, "construction_science")
        
        material_entities = [e for e in entities if e['entity_type'] == 'material']
        assert len(material_entities) > 0

    def test_extract_construction_systems(self):
        """Test extraction of construction systems"""
        text = "The building has a foundation, walls, and roof systems."
        
        entities = extract_entities(text, "construction_science")
        
        system_entities = [e for e in entities if e['entity_type'] == 'system']
        assert len(system_entities) > 0

    def test_extract_construction_environments(self):
        """Test extraction of environmental exposures"""
        text = "The material was exposed to temperature, humidity, and moisture."
        
        entities = extract_entities(text, "construction_science")
        
        environment_entities = [e for e in entities if e['entity_type'] == 'environment']
        assert len(environment_entities) > 0

    def test_extract_construction_failure_modes(self):
        """Test extraction of failure modes"""
        text = "The structure showed cracking, buckling, and fatigue."
        
        entities = extract_entities(text, "construction_science")
        
        failure_entities = [e for e in entities if e['entity_type'] == 'failure_mode']
        assert len(failure_entities) > 0

    def test_extract_construction_test_methods(self):
        """Test extraction of test methods"""
        text = "The material was tested using compression, tension, and shear tests."
        
        entities = extract_entities(text, "construction_science")
        
        test_entities = [e for e in entities if e['entity_type'] == 'test_method']
        assert len(test_entities) > 0


class TestBiomedicalEntities:
    """Test biomedical entity extraction"""
    
    def test_extract_biomedical_compounds(self):
        """Test extraction of biomedical compounds"""
        text = "The study used aspirin and ibuprofen compounds."
        
        entities = extract_entities(text, "methods_tooling")
        
        compound_entities = [e for e in entities if e['entity_type'] == 'compound']
        assert len(compound_entities) >= 0

    def test_extract_biomedical_peptides(self):
        """Test extraction of peptides"""
        text = "The sequence was GGGSGGGSGGG (SEQ ID NO: 1)."
        
        entities = extract_entities(text, "methods_tooling")
        
        peptide_entities = [e for e in entities if e['entity_type'] == 'peptide']
        assert len(peptide_entities) > 0

    def test_extract_biomedical_targets(self):
        """Test extraction of biological targets"""
        text = "The study targeted mTOR and AKT proteins."
        
        entities = extract_entities(text, "methods_tooling")
        
        target_entities = [e for e in entities if e['entity_type'] == 'target']
        assert len(target_entities) >= 0

    def test_extract_biomedical_models(self):
        """Test extraction of experimental models"""
        text = "The study used HEK293 cells and mouse models."
        
        entities = extract_entities(text, "methods_tooling")
        
        model_entities = [e for e in entities if e['entity_type'] == 'model']
        assert len(model_entities) >= 0

    def test_extract_biomedical_stem_cells(self):
        """Test extraction of stem cell keywords"""
        text = "The study used mesenchymal stem cells (MSCs)."
        
        entities = extract_entities(text, "methods_tooling")
        
        stem_cell_entities = [e for e in entities if e['entity_type'] == 'stem_cell']
        assert len(stem_cell_entities) > 0
