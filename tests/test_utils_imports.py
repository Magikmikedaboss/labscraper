# Smoke import/no-op tests for zero-coverage and rarely-used utils modules
import importlib
import pytest

MODULES = [
    'utils.check_target_in_pdfs',
    'utils.check_recent_run',
    'utils.check_output_files',
    'utils.check_neural_cell_results',
    'utils.check_neural_cells',
    'utils.check_longevity_compounds',
    'utils.check_entity_types',
    'utils.check_db_schema',
    'utils.check_confidence',
    'utils.check_compound_extraction',
    'utils.check_biohacking_compounds',
    'utils.demo_domain_export',
    'utils.export_utilities',
    'utils.export_pattern_intelligence',
    'utils.export_dual_lens',
    'utils.export_csv',
    'utils.entity_extractor',
    'utils.integrated_entity_system',
    'utils.overlay_scorer',
    'utils.enhanced_entity_extractor',
    'utils.lint_seeds',
    'utils.seed_overlay_loader',
    'utils.verify_setup',
    'utils.view_pattern_export',
    'utils.show_all_exports',
    'utils.show_v4_exports',
    'utils.pdf_metadata_parser',
    'utils.process_words',
    'utils.domain_enforcement',
    'utils.cleanup_obsolete',
    'utils.init_construction_db',
    'utils.init_db',
    'utils.init_test_db',
]

@pytest.mark.parametrize('modname', MODULES)
def test_import_module(modname):
    module = importlib.import_module(modname)
    assert module is not None, f"importlib.import_module({modname}) returned None"
