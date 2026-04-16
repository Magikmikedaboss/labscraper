"""Tests for configuration validation using pytest"""
import tempfile
from pathlib import Path
from utils.run_engine import load_seed_file


class TestConfigValidation:
    """Test configuration validation functionality"""
    
    def test_load_seed_file_valid(self):
        """Test loading valid seed file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create seed file
            seed_file = Path(temp_dir) / "test_seeds.txt"
            seed_file.write_text("# Test seed file\ncompound1\ncompound2\n# Comment line\ncompound3\n")
            
            seeds = load_seed_file(seed_file, case="lower")
            
            assert len(seeds) == 3
            assert 'compound1' in seeds
            assert 'compound2' in seeds
            assert 'compound3' in seeds
            assert 'comment line' not in seeds

    def test_load_seed_file_missing(self):
        """Test loading missing seed file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            seed_file = Path(temp_dir) / "missing_seeds.txt"
            
            seeds = load_seed_file(seed_file, case="lower")
            
            assert seeds == set()

    def test_load_seed_file_empty(self):
        """Test loading empty seed file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            seed_file = Path(temp_dir) / "empty_seeds.txt"
            seed_file.write_text("")
            
            seeds = load_seed_file(seed_file, case="lower")
            
            assert seeds == set()

    def test_load_seed_file_only_comments(self):
        """Test loading seed file with only comments"""
        with tempfile.TemporaryDirectory() as temp_dir:
            seed_file = Path(temp_dir) / "comments_only.txt"
            seed_file.write_text("# This is a comment\n# Another comment\n")
            
            seeds = load_seed_file(seed_file, case="lower")
            
            assert seeds == set()

    def test_load_seed_file_mixed_content(self):
        """Test loading seed file with mixed content"""
        with tempfile.TemporaryDirectory() as temp_dir:
            seed_file = Path(temp_dir) / "mixed_seeds.txt"
            seed_file.write_text("valid_seed1\n# Comment\nvalid_seed2\n\n# Another comment\nvalid_seed3\n")
            
            seeds = load_seed_file(seed_file, case="lower")
            
            assert len(seeds) == 3
            assert 'valid_seed1' in seeds
            assert 'valid_seed2' in seeds
            assert 'valid_seed3' in seeds
            assert 'comment' not in seeds

    def test_load_seed_file_case_insensitive(self):
        """Test that seed loading is case insensitive"""
        with tempfile.TemporaryDirectory() as temp_dir:
            seed_file = Path(temp_dir) / "case_seeds.txt"
            seed_file.write_text("UPPERCASE\nlowercase\nMixedCase\n")
            
            seeds = load_seed_file(seed_file, case="lower")
            
            assert len(seeds) == 3
            assert 'uppercase' in seeds
            assert 'lowercase' in seeds
            assert 'mixedcase' in seeds
            assert 'UPPERCASE' not in seeds  # Should be converted to lowercase
            assert 'lowercase' in seeds
            assert 'MixedCase' not in seeds  # Should be converted to lowercase
