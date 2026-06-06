# Smoke import/no-op tests for zero-coverage and rarely-used utils modules
import importlib
import pytest
import pkgutil
import utils

# Dynamically discover all modules in utils and subpackages
MODULES = [
    modname for _, modname, _ in pkgutil.walk_packages(utils.__path__, prefix='utils.')
]

@pytest.mark.parametrize('modname', MODULES)
def test_import_module(modname):
    """
    Test that each module in MODULES can be imported without raising an exception.
    This verifies that all listed modules are importable and have no import-time errors.
    """
    importlib.import_module(modname)
