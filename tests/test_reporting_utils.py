import tempfile
from pathlib import Path
import utils.reporting_utils as reporting_utils

def test_write_run_meta_creates_output_file():
    confidence_changes = {}
    canonical_entities = {('type', 'name'): {
        'event_count': 1,
        'paper_ids': set(),
        'original_names': set(),
        'entity_name': 'name',
        'entity_type': 'type',
        'entity_variant': '',
        'role': 'primary',
    }}
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        reporting_utils.write_run_meta(confidence_changes, canonical_entities, domain_id="test", output_dir=output_dir)
        # Check that a meta file was created in the output directory
        found = list(output_dir.glob("**/run_meta*.json"))
        assert found, "No run_meta*.json file created by write_run_meta"
        # Open and validate the JSON file
        meta_path = found[0]
        with open(meta_path, "r", encoding="utf-8") as f:
            data = f.read()
            assert data.strip(), "run_meta*.json file is empty"
            meta = None
            try:
                import json
                meta = json.loads(data)
            except Exception as e:
                assert False, f"run_meta*.json is not valid JSON: {e}"
        # Assert on expected structure and key fields
        assert isinstance(meta, dict), "run_meta*.json root is not a dict"
        for key in ["run_id", "timestamp", "engine_version", "counts", "confidence_distribution", "top_entities"]:
            assert key in meta, f"Missing key in run_meta*.json: {key}"
        assert isinstance(meta["run_id"], str) and meta["run_id"], "run_id should be a non-empty string"
        assert isinstance(meta["timestamp"], str) and meta["timestamp"], "timestamp should be a non-empty string"
        assert isinstance(meta["counts"], dict), "counts should be a dict"
        assert isinstance(meta["confidence_distribution"], dict), "confidence_distribution should be a dict"
