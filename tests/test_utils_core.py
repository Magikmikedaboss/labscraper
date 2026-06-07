import sqlite3
import tempfile
from utils import db_utils, event_classification, data_extractors, entities, common, text_utils
from utils.event_classification import ConfidenceInput

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
    assert isinstance(dec, str)
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
    conf = event_classification.confidence_score(
        ConfidenceInput(
            has_entity=True,
            method_tags=tags,
            failure_reason=reason,
            decision_taken=dec,
            has_measurements=True,
            sentence_l=s
        )
    )
    assert isinstance(conf, str)

def test_data_extractors_quantitative():
    s = "IC50 was 12.5 nM and half-life was 3 hours."
    measurements = data_extractors.extract_quantitative_data(s)
    assert any(m['measurement_type'] == 'ic50' for m in measurements)
    assert any(m['measurement_type'] == 'half_life' for m in measurements)

def test_entities_extract_compounds_targets(monkeypatch):
    # Patch get_compound_seeds and get_target_seeds
    monkeypatch.setattr(entities, 'get_compound_seeds', lambda resolved_dir=None: ['aspirin'])
    monkeypatch.setattr(entities, 'get_target_seeds', lambda resolved_dir=None: ['mtor'])
    s = "Aspirin inhibits mTOR."
    compounds = entities.extract_compounds(s)
    targets = entities.extract_targets(s)
    assert any(c['entity_name'] == 'ASPIRIN' for c in compounds)
    assert any(t['entity_name'] == 'MTOR' for t in targets)

def test_common_sha_and_temp():
    s = "test string"
    assert len(common.sha256_short(s)) == 16
    assert len(common.sha256_hex(s)) == 64
    # is_temp_dir should work for temp and non-temp
    assert isinstance(common.is_temp_dir(tempfile.gettempdir()), bool)
    assert isinstance(common.is_temp_dir("/"), bool)

def test_text_utils_chunk_and_guess():
    text = "This is a sentence. This is another! And a third?"
    chunks = text_utils.chunk_sentences(text)
    # Should return exactly 3 chunks (one per sentence)
    assert len(chunks) == 3
    # Check that each chunk ends with sentence punctuation
    for i, chunk in enumerate(chunks):
        assert chunk, "Empty chunk returned by chunk_sentences"
        assert chunk[-1] in ".!?", f"Chunk does not end with punctuation: {chunk!r}"
        # If not last chunk, next chunk should start with uppercase letter
        if i < len(chunks) - 1:
            next_chunk = chunks[i+1]
            assert next_chunk, "Empty next_chunk returned by chunk_sentences"
            assert next_chunk[0].isupper(), f"Next chunk does not start with uppercase: {next_chunk!r}"
    # Check that joining chunks (with single spaces) matches the original text (ignoring multiple spaces)
    joined = " ".join(chunks)
    def normalize_spaces(s):
        return " ".join(s.split())
    assert normalize_spaces(joined) == normalize_spaces(text)
    assert text_utils.guess_stage("in vivo mouse study") == "in_vivo"
    assert text_utils.guess_section("methods and results") == "mixed"
    assert text_utils.guess_section("methods only") == "methods"
    assert text_utils.guess_section("results only") == "results"
    assert text_utils.guess_section("discussion section") == "discussion"
    assert text_utils.guess_section("random text") == "unknown"
