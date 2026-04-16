"""Tests for domain loading functionality using pytest"""
import json
import tempfile
from pathlib import Path
from utils.run_engine import get_seeds
from utils.axon_domains import get_domain_by_id


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
            
            # Change working directory to temp_dir and clear cache
            import utils.run_engine
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
                
                assert len(compounds) == 2
                assert len(_targets) == 2
                assert len(_models) == 2
                assert len(stopwords) == 2
                assert 'compound1' in compounds
                assert 'target1' in _targets
                assert 'model1' in _models
                assert 'stopword1' in stopwords
            finally:
                os.chdir(original_cwd)

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
            
            # Change working directory to temp_dir and clear cache
            import utils.run_engine
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
                
                assert len(compounds) == 2
                assert len(_targets) == 0
                assert len(_models) == 0
                assert len(stopwords) == 0
            finally:
                os.chdir(original_cwd)

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
            
            # Change working directory to temp_dir and clear cache
            import utils.run_engine
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
                
                assert len(compounds) == 0
                assert len(_targets) == 0
                assert len(_models) == 0
                assert len(stopwords) == 0
            finally:
                os.chdir(original_cwd)

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
            
            # Change working directory to temp_dir and clear cache
            import utils.run_engine
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
                
                assert len(compounds) == 2
                assert 'compound1' in compounds
                assert 'compound2' in compounds
                assert 'comment' not in compounds
            finally:
                os.chdir(original_cwd)

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
            
            # Change working directory to temp_dir and clear cache
            import utils.run_engine
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
                
                assert len(compounds) == 3
                assert 'uppercase' in compounds
                assert 'lowercase' in compounds
                assert 'mixedcase' in compounds
                assert 'UPPERCASE' not in compounds  # Should be converted to lowercase
                assert 'lowercase' in compounds
                assert 'MixedCase' not in compounds  # Should be converted to lowercase
            finally:
                os.chdir(original_cwd)

    def test_get_seeds_no_seeds_directory(self):
        """Test behavior when no seeds directory exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Don't create seeds directory
            # Change working directory to temp_dir and clear cache
            import utils.run_engine
            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)
                
                compounds, _targets, _models, stopwords = get_seeds()
                
                assert len(compounds) == 0
                assert len(_targets) == 0
                assert len(_models) == 0
                assert len(stopwords) == 0
            finally:
                os.chdir(original_cwd)

    def test_get_domain_by_id_falls_back_to_config_domains(self):
        """Domain lookup should support the current production config/domains layout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_domains = Path(temp_dir) / "config" / "domains"
            config_domains.mkdir(parents=True)
            (config_domains / "biohacking_longevity.json").write_text(
                json.dumps({
                    "id": "biohacking_longevity",
                    "name": "Biohacking & Longevity",
                    "description": "Observational longevity lens"
                }),
                encoding="utf-8",
            )

            original_cwd = Path.cwd()
            try:
                import os
                os.chdir(temp_dir)

                profile = get_domain_by_id("biohacking_longevity")

                assert profile is not None
                assert profile.id == "biohacking_longevity"
                assert profile.name == "Biohacking & Longevity"
            finally:
                os.chdir(original_cwd)
