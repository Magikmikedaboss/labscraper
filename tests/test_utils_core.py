import pytest
import sqlite3
import tempfile
from pathlib import Path
from utils import db_utils, event_classification, data_extractors, entities, common, text_utils

def test_connect_db_and_get_tables(tmp_path):
    # Create a temp db
    db_file = tmp_path / "test.sqlite"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE foo (id INTEGER)")
    conn.commit()
    conn.close()
    # Test connect_db
    c = db_utils.connect_db(str(db_file))
    assert "foo" in db_utils.get_tables(c)
    stats = db_utils.get_table_stats(c, "foo")
    assert "columns" in stats and "count" in stats
    c.close()

def test_event_classification_basic():
    s = "The sample was rapidly degraded and not pursued further."
    tags = event_classification.detect_method_tags(s)
    assert isinstance(tags, list)
    reason = event_classification.detect_failure_reason(s)
    assert reason in event_classification.FAILURE_PHRASES or reason == "unknown"
    # Decision
    dec = event_classification.detect_decision(s)
    assert isinstance(dec, tuple)
    # Outcome
    out = event_classification.detect_outcome(s)
    assert isinstance(out, str)
    # Classify
    etype = event_classification.classify_event_type(s, tags, reason, dec)
    assert isinstance(etype, str)
    # Evidence strength
    strength = event_classification.evidence_strength(s)
    assert isinstance(strength, str)
    # Confidence
    conf = event_classification.confidence_score(True, tags, reason, dec, True, s)
    assert isinstance(conf, str)

def test_data_extractors_quantitative():
    s = "IC50 was 12.5 nM and half-life was 3 hours."
    measurements = data_extractors.extract_quantitative_data(s)
    assert any(m['measurement_type'] == 'ic50' for m in measurements)
    assert any(m['measurement_type'] == 'half_life' for m in measurements)

def test_entities_extract_compounds_targets(monkeypatch):
    # Patch _get_compound_seeds and _get_target_seeds
    monkeypatch.setattr(entities, '_get_compound_seeds', lambda SEEDS_DIR=None: ['aspirin'])
    monkeypatch.setattr(entities, '_get_target_seeds', lambda SEEDS_DIR=None: ['mtor'])
    s = "Aspirin inhibits mTOR."
    compounds = entities.extract_compounds(s)
    targets = entities.extract_targets(s)
    assert any(c['entity_name'] == 'ASPIRIN' for c in compounds)
    assert any(t['entity_name'] == 'MTOR' for t in targets)

def test_common_sha_and_temp():
    s = "test string"
    assert len(common.sha16(s)) == 16
    assert len(common.sha64(s)) == 64
    # _is_temp_dir should work for temp and non-temp
    assert isinstance(common._is_temp_dir(tempfile.gettempdir()), bool)
    assert isinstance(common._is_temp_dir("/"), bool)

def test_text_utils_chunk_and_guess():
    text = "This is a sentence. This is another! And a third?"
    chunks = text_utils.chunk_sentences(text)
    assert len(chunks) == 3
    assert text_utils.guess_stage("in vivo mouse study") == "in_vivo"
    assert text_utils.guess_section("methods and results") == "mixed"
    assert text_utils.guess_section("methods only") == "methods"
    assert text_utils.guess_section("results only") == "results"
    assert text_utils.guess_section("discussion section") == "discussion"
    assert text_utils.guess_section("random text") == "unknown"
