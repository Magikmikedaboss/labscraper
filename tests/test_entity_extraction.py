"""Tests for entity extraction functionality using pytest"""

import pytest

from utils.entities import extract_entities
from utils.entities import extract_compounds
from utils.entities import extract_targets, extract_models
from utils.entities import extract_biomedical_entities
from utils.entities import _find_specific_failure_phrases


class TestEntityExtraction:
    """Test basic entity extraction functionality"""

    def test_extract_entities_methods_tooling_domain(self):
        """Test entity extraction for methods_tooling domain"""
        text = "The study used CRISPR-Cas9 to edit the TP53 gene in human stem cells."

        entities = extract_entities(text, "methods_tooling")

        # Should extract compounds, peptides, targets, models, and stem cells
        assert len(entities) > 0
        entity_types = [e["entity_type"] for e in entities]
        assert (
            "compound" in entity_types
            or "peptide" in entity_types
            or "target" in entity_types
        )

    def test_extract_entities_construction_science_domain(self):
        """Test entity extraction for construction_science domain"""
        text = "The concrete beam was tested under load conditions with steel reinforcement."

        entities = extract_entities(text, "construction_science")

        # Should extract construction-specific entities
        assert len(entities) > 0
        entity_types = [e["entity_type"] for e in entities]
        expected = ["material", "system"]
        assert set(expected).issubset(set(entity_types))

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
        assert isinstance(compounds, list)
        # Assert expected compounds are present
        assert any(
            "aspirin" in ((c.get("entity_name") or "") + (c.get("text") or "")).lower()
            for c in compounds
        )

    def test_extract_targets(self):
        """Test target extraction"""
        text = "The study targeted mTOR and AKT signaling pathways."
        targets = extract_targets(text)
        assert isinstance(targets, list)
        # Assert expected targets are present
        assert any("MTOR" == t.get("entity_name") for t in targets)
        assert any("AKT" == t.get("entity_name") for t in targets)

    def test_extract_models(self):
        """Test model extraction"""
        text = "The study used HEK293 cells and mouse models."
        models = extract_models(text)
        assert isinstance(models, list)
        # Assert expected models are present
        assert any("HEK293" == m.get("entity_name") for m in models)
        assert any("MOUSE" == m.get("entity_name") for m in models)


class TestConstructionEntities:
    """Test construction science entity extraction"""

    def test_extract_construction_materials(self):
        """Test extraction of construction materials"""
        text = "The study used concrete, steel, and wood materials."

        entities = extract_entities(text, "construction_science")

        material_entities = [e for e in entities if e["entity_type"] == "material"]
        assert len(material_entities) > 0

    def test_extract_construction_systems(self):
        """Test extraction of construction systems"""
        text = "The building has a foundation, walls, and roof systems."

        entities = extract_entities(text, "construction_science")

        system_entities = [e for e in entities if e["entity_type"] == "system"]
        assert len(system_entities) > 0

    def test_extract_construction_environments(self):
        """Test extraction of environmental exposures"""
        text = "The material was exposed to temperature, humidity, and moisture."

        entities = extract_entities(text, "construction_science")

        environment_entities = [
            e for e in entities if e["entity_type"] == "environment"
        ]
        assert len(environment_entities) > 0

    def test_extract_construction_failure_modes(self):
        """Test extraction of failure modes"""
        text = "The structure showed cracking, buckling, and fatigue."

        entities = extract_entities(text, "construction_science")

        failure_entities = [e for e in entities if e["entity_type"] == "failure_mode"]
        assert len(failure_entities) > 0

    def test_find_specific_failure_phrases(self):
        phrases = _find_specific_failure_phrases(
            "The beam experienced shear failure and crack due to fatigue under load."
        )

        assert "shear failure" in phrases
        assert any("crack due to fatigue" in phrase for phrase in phrases)

    def test_extract_construction_test_methods(self):
        """Test extraction of test methods"""
        text = "The material was tested using compression, tension, and shear tests."

        entities = extract_entities(text, "construction_science")

        test_entities = [e for e in entities if e["entity_type"] == "test_method"]
        assert len(test_entities) > 0


class TestBiomedicalEntities:
    """Test biomedical entity extraction"""

    def test_extract_biomedical_compounds(self):
        """Test extraction of biomedical compounds"""
        text = "The study used aspirin and ibuprofen compounds."
        entities = extract_entities(text, "methods_tooling")
        compound_entities = [e for e in entities if e["entity_type"] == "compound"]
        assert len(compound_entities) > 0
        # Build lowercased text for each entity for easier checks
        lowercased_texts = [
            (e.get("entity_name", "") + e.get("text", "")).lower()
            for e in compound_entities
        ]
        # Assert that "aspirin" and "ibuprofen" are found in at least one entity each
        assert any("aspirin" in t for t in lowercased_texts)
        assert any("ibuprofen" in t for t in lowercased_texts)

    def test_extract_biomedical_peptides(self):
        """Test extraction of peptides"""
        text = "The sequence was GGGSGGGSGGG (SEQ ID NO: 1)."

        entities = extract_entities(text, "methods_tooling")

        peptide_entities = [e for e in entities if e["entity_type"] == "peptide"]
        assert len(peptide_entities) > 0
        # Assert the expected peptide sequence is present in the extracted entity
        assert any(
            ("GGGSGGGSGGG" in e.get("entity_name", ""))
            or ("GGGSGGGSGGG" in e.get("text", ""))
            for e in peptide_entities
        )

    def test_extract_biomedical_targets(self):
        """Test extraction of biological targets"""
        text = "The study targeted mTOR and AKT proteins."
        entities = extract_entities(text, "methods_tooling")
        target_entities = [e for e in entities if e["entity_type"] == "target"]
        assert len(target_entities) > 0
        def matches_target(e):
            combined = (e.get("entity_name", "") + e.get("text", "")).lower()
            return "mtor" in combined or "akt" in combined
        found_target = any(matches_target(e) for e in target_entities)
        assert found_target

    def test_extract_biomedical_models(self):
        """Test extraction of experimental models"""
        text = "The study used HEK293 cells and mouse models."
        entities = extract_entities(text, "methods_tooling")
        model_entities = [e for e in entities if e["entity_type"] == "model"]
        assert len(model_entities) > 0
        matched_entities = [
            e for e in model_entities
            if "hek293" in (e.get("entity_name", "") + e.get("text", "")).lower()
            or "mouse" in (e.get("entity_name", "") + e.get("text", "")).lower()
        ]
        assert matched_entities

    def test_extract_biomedical_stem_cells(self):
        """Test extraction of stem cell keywords"""
        text = "The study used mesenchymal stem cells (MSCs)."

        entities = extract_entities(text, "methods_tooling")

        stem_cell_entities = [e for e in entities if e["entity_type"] == "stem_cell"]
        assert len(stem_cell_entities) > 0
        assert any(e.get("entity_variant") == "stem_cell" for e in stem_cell_entities)

    def test_extract_biomedical_stem_and_neural_cell_variants(self):
        """Test descriptive variants and dedup normalization for stem/neural cells"""
        text = "Mesenchymal stem cells and microglia were analyzed together."
        extracted_names = set()

        entities = extract_biomedical_entities(text, extracted_names)

        stem_entities = [e for e in entities if e["entity_type"] == "stem_cell"]
        neural_entities = [e for e in entities if e["entity_type"] == "neural_cell"]

        assert stem_entities
        assert neural_entities
        assert all(e.get("entity_variant") == "stem_cell" for e in stem_entities)
        assert all(e.get("entity_variant") == "neural_cell" for e in neural_entities)
        assert "mesenchymal" in extracted_names
        assert "microglia" in extracted_names


@pytest.mark.parametrize(
    "word",
    ["CANADIAN", "CLIMATE", "PREFACE", "PRINCIPAL", "SERVICE", "PACIFIC"],
)
def test_biomedical_peptide_denylist_blocks_obvious_false_positives(word):
    text = f"The term {word} appears in the document."

    entities = extract_entities(text, "methods_tooling")

    assert not any(
        e["entity_type"] == "peptide"
        and word.lower() == (e.get("entity_name") or e.get("text") or "").lower()
        for e in entities
    )
