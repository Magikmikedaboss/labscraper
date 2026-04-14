"""Tests for entity extraction across the 4 biomedical research domains:
neuroscience_cognition, biohacking_longevity, drug_discovery, stem_cells_regen
"""
from utils.run_engine import extract_entities


class TestNeuroscienceCognitionDomain:
    """Entity extraction for the neuroscience_cognition domain."""

    def test_neural_cell_types_extracted(self):
        """Microglia, astrocytes, and neurons should be tagged as neural_cell."""
        text = "Activated microglia and reactive astrocytes were observed in the cortex."
        entities = extract_entities(text, "neuroscience_cognition")
        assert len(entities) > 0
        types = [e["entity_type"] for e in entities]
        assert "neural_cell" in types

    def test_pathway_target_extracted(self):
        """mTOR pathway target should be extracted from neuroscience text."""
        text = "Inhibition of mTOR signaling reduced neuroinflammation in hippocampal neurons."
        entities = extract_entities(text, "neuroscience_cognition")
        assert len(entities) > 0
        names = [e["entity_name"].upper() for e in entities]
        assert "MTOR" in names

    def test_model_extracted(self):
        """HEK293 or mouse model should be extracted."""
        text = "Experiments were performed in HEK293 cells and in a mouse model of neurodegeneration."
        entities = extract_entities(text, "neuroscience_cognition")
        types = [e["entity_type"] for e in entities]
        assert "model" in types
        assert any("hek293" in e["text"].lower() or "mouse" in e["text"].lower() for e in entities)

    def test_no_entities_from_irrelevant_text(self):
        """Purely generic text without biomedical terms returns no entities."""
        text = "The weather was sunny and warm with pleasant winds."
        entities = extract_entities(text, "neuroscience_cognition")
        assert entities == []

    def test_neuron_entity_type_promoted(self):
        """'neurons' should be typed as neural_cell, not stem_cell or model."""
        text = "Dopaminergic neurons were depleted in the substantia nigra."
        entities = extract_entities(text, "neuroscience_cognition")
        neural = [e for e in entities if e["entity_name"].lower() == "neurons"]
        assert len(neural) > 0, "No 'neurons' entity extracted"
        assert neural[0]["entity_type"] == "neural_cell"


class TestBiohackingLongevityDomain:
    """Entity extraction for the biohacking_longevity domain."""

    def test_everolimus_extracted_as_compound(self):
        """Everolimus is a known longevity compound and should be tagged as compound."""
        text = "Everolimus extended median lifespan in aged mice by activating autophagy."
        entities = extract_entities(text, "biohacking_longevity")
        assert len(entities) > 0
        names = [e["entity_name"].upper() for e in entities]
        assert "EVEROLIMUS" in names

    def test_metformin_compound_extracted(self):
        """Metformin should be extracted as a compound."""
        text = "Metformin treatment reduced all-cause mortality in a cohort study."
        entities = extract_entities(text, "biohacking_longevity")
        names = [e["entity_name"].upper() for e in entities]
        assert "METFORMIN" in names

    def test_mtor_target_in_longevity_context(self):
        """mTOR target should be extracted in a longevity research context."""
        text = "mTOR inhibition is a conserved longevity pathway across species."
        entities = extract_entities(text, "biohacking_longevity")
        assert len(entities) > 0
        names = [e["entity_name"].upper() for e in entities]
        assert "MTOR" in names

    def test_ipsc_stem_cell_longevity(self):
        """iPSC mentioned in longevity contexts should be tagged as stem_cell."""
        text = "iPSC-derived cardiomyocytes showed reduced senescence after NAD+ supplementation."
        entities = extract_entities(text, "biohacking_longevity")
        types = [e["entity_type"] for e in entities]
        assert "stem_cell" in types

    def test_empty_text_returns_no_entities(self):
        text = ""
        assert extract_entities(text, "biohacking_longevity") == []


class TestDrugDiscoveryDomain:
    """Entity extraction for the drug_discovery domain."""

    def test_compound_extracted(self):
        """A named compound (semaglutide) should be extracted and typed as compound."""
        text = "Semaglutide inhibited GLP-1R with an IC50 of 0.17 µM in the enzyme assay."
        entities = extract_entities(text, "drug_discovery")
        assert len(entities) > 0
        types = [e["entity_type"] for e in entities]
        assert "compound" in types

    def test_target_protein_extracted(self):
        """A biological target (AKT) should be extracted."""
        text = "AKT phosphorylation was significantly reduced following treatment with the compound."
        entities = extract_entities(text, "drug_discovery")
        names = [e["entity_name"].upper() for e in entities]
        assert "AKT" in names

    def test_multiple_entities_in_one_sentence(self):
        """Both compound and target can appear in the same sentence."""
        text = "Aspirin inhibited mTOR at nanomolar concentrations in the binding assay."
        entities = extract_entities(text, "drug_discovery")
        types = {e["entity_type"] for e in entities}
        assert "compound" in types, "Compound not found"
        assert "target" in types, "Target not found"
        assert len(entities) >= 2, "Less than two entities extracted"

    def test_model_in_drug_discovery(self):
        """Cell line models used in drug discovery should be extractable."""
        text = "The compound was screened in HEK293 cells and showed selective activity."
        entities = extract_entities(text, "drug_discovery")
        types = [e["entity_type"] for e in entities]
        assert "model" in types, "Model not found in drug discovery extraction"

    def test_no_entities_generic_text(self):
        """Non-scientific prose returns empty list."""
        text = "The quarterly report was approved by the board of directors."
        entities = extract_entities(text, "drug_discovery")
        assert entities == []


class TestStemCellsRegenDomain:
    """Entity extraction for the stem_cells_regen domain."""

    def test_ipsc_extracted_as_stem_cell(self):
        """iPSC should be typed as stem_cell."""
        text = "iPSC-derived organoids recapitulated the key features of human intestinal epithelium."
        entities = extract_entities(text, "stem_cells_regen")
        types = [e["entity_type"] for e in entities]
        assert "stem_cell" in types

    def test_msc_extracted_as_stem_cell(self):
        """MSC should be extracted and typed as stem_cell."""
        text = "MSC transplantation promoted bone regeneration in the rat femur defect model."
        entities = extract_entities(text, "stem_cells_regen")
        names = [e["entity_name"].upper() for e in entities]
        assert "MSC" in names
        stem = [e for e in entities if e["entity_name"].upper() == "MSC"]
        assert stem[0]["entity_type"] == "stem_cell"

    def test_organoid_typed_as_model(self):
        """'organoid' appears in model names set and should be typed as model."""
        text = "Brain organoids derived from iPSCs showed spontaneous neural activity."
        entities = extract_entities(text, "stem_cells_regen")
        types = [e["entity_type"] for e in entities]
        assert "model" in types, "Organoid not typed as model"

    def test_target_extracted_from_regen_context(self):
        """Well-known regen targets like mTOR should still be extractable."""
        text = "mTOR signaling drives proliferation in MSC populations after injury."
        entities = extract_entities(text, "stem_cells_regen")
        names = [e["entity_name"].upper() for e in entities]
        assert "MTOR" in names, "mTOR not extracted as target in regen context"

    def test_empty_text_returns_empty_list(self):
        assert extract_entities("", "stem_cells_regen") == []
