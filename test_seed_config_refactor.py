#!/usr/bin/env python3
"""
Test script to verify that the SeedConfig refactoring works correctly.
This ensures that the global mutable state has been eliminated and the
new SeedConfig dataclass is working properly.
"""

import sys
import os
from pathlib import Path

# Add the utils directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent / "utils"))

def test_seed_config_import():
    """Test that we can import the SeedConfig class"""
    try:
        from utils.scrape_pdfs_phase1 import SeedConfig, _seed_config  # type: ignore
        print("✅ Successfully imported SeedConfig and _seed_config")
        return True
    except ImportError as e:
        print(f"⚠️  SeedConfig refactoring not yet implemented: {e}")
        print("   This test expects a scrape_pdfs_phase1.py file with SeedConfig class")
        return False

def test_seed_config_initialization():
    """Test that SeedConfig can be initialized properly"""
    try:
        from utils.scrape_pdfs_phase1 import SeedConfig  # type: ignore
        
        # Test initialization with some sample data
        config = SeedConfig(
            compounds={"compound1", "compound2"},
            targets={"target1", "target2"},
            models={"model1", "model2"},
            assays={"assay1", "assay2"},
            indications={"indication1", "indication2"},
            stopwords={"stopword1", "stopword2"}
        )
        
        # Verify all fields are set correctly
        assert len(config.compounds) == 2
        assert len(config.targets) == 2
        assert len(config.models) == 2
        assert len(config.assays) == 2
        assert len(config.indications) == 2
        assert len(config.stopwords) == 2
        
        print("✅ SeedConfig initialization works correctly")
        return True
    except Exception as e:
        print(f"❌ SeedConfig initialization failed: {e}")
        return False

def test_default_factory():
    """Test that SeedConfig uses default_factory correctly"""
    try:
        from utils.scrape_pdfs_phase1 import SeedConfig  # type: ignore
        
        # Test initialization with default values
        config = SeedConfig()
        
        # Verify all fields are sets (not None)
        assert isinstance(config.compounds, set)
        assert isinstance(config.targets, set)
        assert isinstance(config.models, set)
        assert isinstance(config.assays, set)
        assert isinstance(config.indications, set)
        assert isinstance(config.stopwords, set)
        
        # Verify they are empty sets
        assert len(config.compounds) == 0
        assert len(config.targets) == 0
        assert len(config.models) == 0
        assert len(config.assays) == 0
        assert len(config.indications) == 0
        assert len(config.stopwords) == 0
        
        print("✅ SeedConfig default_factory works correctly")
        return True
    except Exception as e:
        print(f"❌ SeedConfig default_factory failed: {e}")
        return False

def test_module_level_instance():
    """Test that the module-level _seed_config is properly initialized"""
    try:
        import importlib
        import utils.scrape_pdfs_phase1  # type: ignore
        importlib.reload(utils.scrape_pdfs_phase1)
        from utils.scrape_pdfs_phase1 import _seed_config, SeedConfig  # type: ignore
        original_seed_config = utils.scrape_pdfs_phase1._seed_config
        try:
            # Initially should be None (after reload)
            assert _seed_config is None

            # Create a new instance
            new_config = SeedConfig(
                compounds={"test_compound"},
                targets={"test_target"}
            )

            # Assign to module level
            utils.scrape_pdfs_phase1._seed_config = new_config

            # Verify it was set correctly
            assert utils.scrape_pdfs_phase1._seed_config is not None
            assert len(utils.scrape_pdfs_phase1._seed_config.compounds) == 1
            assert len(utils.scrape_pdfs_phase1._seed_config.targets) == 1

            print("✅ Module-level _seed_config works correctly")
            return True
        finally:
            utils.scrape_pdfs_phase1._seed_config = original_seed_config
    except Exception as e:
        print(f"❌ Module-level _seed_config failed: {e}")
        return False

def test_no_global_mutable_state():
    """Test that we've eliminated global mutable state"""
    try:
        # Import the module
        import utils.scrape_pdfs_phase1  # type: ignore
        
        # Check that the old global variables are no longer present
        old_globals = ['COMPOUND_SEED_LIST', 'TARGET_SEED_LIST', 'MODEL_SEED_LIST', 
                      'ASSAY_SEED_LIST', 'INDICATION_SEED_LIST', 'STOPWORD_SEED_LIST']
        
        for old_global in old_globals:
            if hasattr(utils.scrape_pdfs_phase1, old_global):
                print(f"❌ Old global variable {old_global} still exists")
                return False
        
        # Check that SeedConfig and _seed_config exist
        if not hasattr(utils.scrape_pdfs_phase1, 'SeedConfig'):
            print("❌ SeedConfig class not found")
            return False
        
        if not hasattr(utils.scrape_pdfs_phase1, '_seed_config'):
            print("❌ _seed_config module variable not found")
            return False
        
        print("✅ Global mutable state has been eliminated")
        return True
    except Exception as e:
        print(f"❌ Global mutable state test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing SeedConfig refactoring...")
    print("=" * 50)
    
    tests = [
        test_seed_config_import,
        test_seed_config_initialization,
        test_default_factory,
        test_module_level_instance,
        test_no_global_mutable_state
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! SeedConfig refactoring is successful.")
        return 0
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())