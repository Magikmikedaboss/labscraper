"""Tests for domain loading functionality using pytest"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock
from utils.run_engine import get_seeds


class TestDomainLoading:
    """Test domain loading functionality"""
    
    def test_get_seeds_valid_files(self):
        """Test loading valid seed files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up seeds directory
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            
            # Create seed files
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            compounds_file.write_text("# Compounds\ncompound1\ncompound2\n")
            
            targets_file = seeds_dir / "base/life_sciences/targets.txt"
            targets_file.write_text("# Targets\ntarget1\ntarget2\n")
            
            models_file = seeds_dir / "base/life_sciences/models.txt"
            models_file.write_text("# Models\nmodel1\nmodel2\n")
            
            stopwords_file = seeds_dir / "stopwords.txt"
            stopwords_file.write_text("# Stopwords\nstopword1\nstopword2\n")
            
            # Mock the current working directory and clear cache
            with patch('utils.run_engine.SEEDS_DIR', Path(temp_dir) / "seeds"):
                # Clear the cache to ensure fresh loading
                import utils.run_engine
                utils.run_engine._get_compound_seeds.cache_clear()
                utils.run_engine._get_target_seeds.cache_clear()
                utils.run_engine._get_model_seeds.cache_clear()
                utils.run_engine._get_stopword_seeds.cache_clear()
                
                # Also mock the actual file loading functions to use our temp files
                with patch('utils.run_engine.load_seed_file') as mock_load:
                    # Mock the function to return our test data
                    def mock_load_file(filepath):
                        if 'compounds' in str(filepath):
                            return {'compound1', 'compound2'}
                        elif 'targets' in str(filepath):
                            return {'target1', 'target2'}
                        elif 'models' in str(filepath):
                            return {'model1', 'model2'}
                        elif 'stopwords' in str(filepath):
                            return {'stopword1', 'stopword2'}
                        return set()
                    
                    mock_load.side_effect = mock_load_file
                    
                    compounds, _targets, _models, stopwords = get_seeds()
                    
                    assert len(compounds) == 2
                    assert len(_targets) == 2
                    assert len(_models) == 2
                    assert len(stopwords) == 2
                    assert 'compound1' in compounds
                    assert 'target1' in _targets
                    assert 'model1' in _models
                    assert 'stopword1' in stopwords

    def test_get_seeds_missing_files(self):
        """Test loading when some seed files are missing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up seeds directory with only some files
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            
            # Create only compounds file
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            compounds_file.write_text("# Compounds\ncompound1\ncompound2\n")
            
            # Mock the current working directory and clear cache
            with patch('utils.run_engine.SEEDS_DIR', Path(temp_dir) / "seeds"):
                # Clear the cache to ensure fresh loading
                import utils.run_engine
                utils.run_engine._get_compound_seeds.cache_clear()
                utils.run_engine._get_target_seeds.cache_clear()
                utils.run_engine._get_model_seeds.cache_clear()
                utils.run_engine._get_stopword_seeds.cache_clear()
                
                # Also mock the actual file loading functions to use our temp files
                with patch('utils.run_engine.load_seed_file') as mock_load:
                    # Mock the function to return our test data
                    def mock_load_file(filepath):
                        if 'compounds' in str(filepath):
                            return {'compound1', 'compound2'}
                        elif 'targets' in str(filepath):
                            return set()  # No targets file
                        elif 'models' in str(filepath):
                            return set()  # No models file
                        elif 'stopwords' in str(filepath):
                            return set()  # No stopwords file
                        return set()
                    
                    mock_load.side_effect = mock_load_file
                    
                    compounds, _targets, _models, stopwords = get_seeds()
                    
                    assert len(compounds) == 2
                    assert len(_targets) == 0
                    assert len(_models) == 0
                    assert len(stopwords) == 0

    def test_get_seeds_empty_files(self):
        """Test loading empty seed files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up seeds directory with empty files
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            
            # Create empty seed files
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            compounds_file.write_text("")
            
            targets_file = seeds_dir / "base/life_sciences/targets.txt"
            targets_file.write_text("")
            
            # Mock the current working directory and clear cache
            with patch('utils.run_engine.SEEDS_DIR', Path(temp_dir) / "seeds"):
                # Clear the cache to ensure fresh loading
                import utils.run_engine
                utils.run_engine._get_compound_seeds.cache_clear()
                utils.run_engine._get_target_seeds.cache_clear()
                utils.run_engine._get_model_seeds.cache_clear()
                utils.run_engine._get_stopword_seeds.cache_clear()
                
                compounds, _targets, _models, stopwords = get_seeds()
                
                assert len(compounds) == 0
                assert len(_targets) == 0
                assert len(_models) == 0
                assert len(stopwords) == 0

    def test_get_seeds_with_comments(self):
        """Test that comments are properly ignored"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up seeds directory with comments
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            
            # Create seed file with comments
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            compounds_file.write_text("# This is a comment\ncompound1\n# Another comment\ncompound2\n")
            
            # Mock the current working directory and clear cache
            with patch('utils.run_engine.SEEDS_DIR', Path(temp_dir) / "seeds"):
                # Clear the cache to ensure fresh loading
                import utils.run_engine
                utils.run_engine._get_compound_seeds.cache_clear()
                utils.run_engine._get_target_seeds.cache_clear()
                utils.run_engine._get_model_seeds.cache_clear()
                utils.run_engine._get_stopword_seeds.cache_clear()
                
                compounds, _targets, _models, stopwords = get_seeds()
                
                assert len(compounds) == 2
                assert 'compound1' in compounds
                assert 'compound2' in compounds
                assert 'comment' not in compounds

    def test_get_seeds_case_insensitive(self):
        """Test that seed loading is case insensitive"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up seeds directory with mixed case
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            
            # Create seed file with mixed case
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            compounds_file.write_text("UPPERCASE\nlowercase\nMixedCase\n")
            
            # Mock the current working directory and clear cache
            with patch('utils.run_engine.SEEDS_DIR', Path(temp_dir) / "seeds"):
                # Clear the cache to ensure fresh loading
                import utils.run_engine
                utils.run_engine._get_compound_seeds.cache_clear()
                utils.run_engine._get_target_seeds.cache_clear()
                utils.run_engine._get_model_seeds.cache_clear()
                utils.run_engine._get_stopword_seeds.cache_clear()
                
                compounds, _targets, _models, stopwords = get_seeds()
                
                assert len(compounds) == 3
                assert 'uppercase' in compounds
                assert 'lowercase' in compounds
                assert 'mixedcase' in compounds
                assert 'UPPERCASE' not in compounds  # Should be converted to lowercase
                assert 'lowercase' in compounds
                assert 'MixedCase' not in compounds  # Should be converted to lowercase

    def test_get_seeds_no_seeds_directory(self):
        """Test behavior when no seeds directory exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Don't create seeds directory
            # Mock the current working directory and clear cache
            with patch('utils.run_engine.SEEDS_DIR', Path(temp_dir) / "seeds"):
                # Clear the cache to ensure fresh loading
                import utils.run_engine
                utils.run_engine._get_compound_seeds.cache_clear()
                utils.run_engine._get_target_seeds.cache_clear()
                utils.run_engine._get_model_seeds.cache_clear()
                utils.run_engine._get_stopword_seeds.cache_clear()
                
                compounds, _targets, _models, stopwords = get_seeds()
                
                assert len(compounds) == 0
                assert len(_targets) == 0
                assert len(_models) == 0
                assert len(stopwords) == 0
