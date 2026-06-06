import json
import tempfile
import gc
import sys
from pathlib import Path
from utils.run_engine import get_seeds
from utils.axon_domains import get_domain_by_id

"""Tests for domain loading functionality using pytest"""

def _tempdir():
    return tempfile.TemporaryDirectory(ignore_cleanup_errors=(sys.platform == "win32"))


class TestDomainLoading:
    """Test domain loading functionality"""
    
    def test_get_seeds_valid_files(self, monkeypatch):
        """Test loading valid seed files"""
        with _tempdir() as temp_dir:
            # Set up seeds directory
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            # Create seed files
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            with open(compounds_file, "w", encoding="utf-8") as f:
                f.write("# Compounds\ncompound1\ncompound2\n")
            targets_file = seeds_dir / "base/life_sciences/targets.txt"
            with open(targets_file, "w", encoding="utf-8") as f:
                f.write("# Targets\ntarget1\ntarget2\n")
            models_file = seeds_dir / "base/life_sciences/models.txt"
            with open(models_file, "w", encoding="utf-8") as f:
                f.write("# Models\nmodel1\nmodel2\n")
            stopwords_file = seeds_dir / "stopwords.txt"
            with open(stopwords_file, "w", encoding="utf-8") as f:
                f.write("# Stopwords\nstopword1\nstopword2\n")
            # Change working directory to temp_dir and clear cache
            monkeypatch.chdir(temp_dir)
            compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
            assert len(compounds) == 2
            assert len(_targets) == 2
            assert len(_models) == 2
            assert len(stopwords) == 2
            assert 'COMPOUND1' in compounds
            assert 'TARGET1' in _targets
            assert 'MODEL1' in _models
            assert 'stopword1' in stopwords
            # Explicitly delete Path objects and collect garbage to avoid Windows file locking issues
            del compounds_file, targets_file, models_file, stopwords_file, seeds_dir
            gc.collect()

    def test_get_seeds_missing_files(self, monkeypatch):
        """Test loading when some seed files are missing"""
        with _tempdir() as temp_dir:
            # Set up seeds directory with only some files
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            # Create only compounds file
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            with open(compounds_file, "w", encoding="utf-8") as f:
                f.write("# Compounds\ncompound1\ncompound2\n")
            # Change working directory to temp_dir and clear cache
            monkeypatch.chdir(temp_dir)
            compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
            assert len(compounds) == 2
            assert len(_targets) == 0
            assert len(_models) == 0
            assert len(stopwords) == 0
            # Explicitly delete Path objects and collect garbage to avoid Windows file locking issues
            del compounds_file, seeds_dir
            gc.collect()

    def test_get_seeds_empty_files(self, monkeypatch):
        """Test loading empty seed files"""
        with _tempdir() as temp_dir:
            # Set up seeds directory with empty files
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            # Create empty seed files
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            with open(compounds_file, "w", encoding="utf-8") as f:
                f.write("")
            targets_file = seeds_dir / "base/life_sciences/targets.txt"
            with open(targets_file, "w", encoding="utf-8") as f:
                f.write("")
            # Change working directory to temp_dir and clear cache
            monkeypatch.chdir(temp_dir)
            compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
            assert len(compounds) == 0
            assert len(_targets) == 0
            assert len(_models) == 0
            assert len(stopwords) == 0
            # Explicitly delete Path objects and collect garbage to avoid Windows file locking issues
            del compounds_file, targets_file, seeds_dir
            gc.collect()

    def test_get_seeds_with_comments(self, monkeypatch):
        """Test that comments are properly ignored"""
        with _tempdir() as temp_dir:
            # Set up seeds directory with comments
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            # Create seed file with comments
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            with open(compounds_file, "w", encoding="utf-8") as f:
                f.write("# This is a comment\ncompound1\n# Another comment\ncompound2\n")
            # Change working directory to temp_dir and clear cache
            monkeypatch.chdir(temp_dir)
            compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
            assert len(compounds) == 2
            assert 'COMPOUND1' in compounds
            assert 'COMPOUND2' in compounds
            # Assert no entry in compounds is a comment line
            assert all(not c.strip().startswith('#') for c in compounds)
            # Explicitly delete Path objects and collect garbage to avoid Windows file locking issues
            del compounds_file, seeds_dir
            gc.collect()

    def test_get_seeds_case_insensitive(self, monkeypatch):
        """Test that seed loading is case insensitive"""
        with _tempdir() as temp_dir:
            # Set up seeds directory with mixed case
            seeds_dir = Path(temp_dir) / "seeds"
            seeds_dir.mkdir()
            # Create seed file with mixed case
            compounds_file = seeds_dir / "base/life_sciences/compounds.txt"
            compounds_file.parent.mkdir(parents=True)
            with open(compounds_file, "w", encoding="utf-8") as f:
                f.write("UPPERCASE\nlowercase\nMixedCase\n")
            # Change working directory to temp_dir and clear cache
            monkeypatch.chdir(temp_dir)
            compounds, _targets, _models, stopwords = get_seeds(SEEDS_DIR=seeds_dir)
            assert len(compounds) == 3
            assert 'UPPERCASE' in compounds
            assert 'LOWERCASE' in compounds
            assert 'MIXEDCASE' in compounds
            assert 'uppercase' not in compounds  # Should be converted to uppercase
            assert 'lowercase' not in compounds
            assert 'MixedCase' not in compounds  # Should be converted to uppercase
            # Explicitly delete Path objects and collect garbage to avoid Windows file locking issues
            del compounds_file, seeds_dir
            gc.collect()

    def test_get_seeds_no_seeds_directory(self, monkeypatch):
        """Test behavior when no seeds directory exists"""
        with _tempdir() as temp_dir:
            # Don't create seeds directory
            # Change working directory to temp_dir and clear cache
            monkeypatch.chdir(temp_dir)
            compounds, _targets, _models, stopwords = get_seeds()
            assert len(compounds) == 0
            assert len(_targets) == 0
            assert len(_models) == 0
            assert len(stopwords) == 0
            # No files created, nothing to delete

    def test_get_domain_by_id_falls_back_to_config_domains(self, monkeypatch):
        """Domain lookup should support the current production config/domains layout."""
        with _tempdir() as temp_dir:
            config_domains = Path(temp_dir) / "config" / "domains"
            config_domains.mkdir(parents=True)

            json_path = config_domains / "biohacking_longevity.json"
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": "biohacking_longevity",
                    "name": "Biohacking & Longevity",
                    "description": "Observational longevity lens"
                }))

            monkeypatch.chdir(temp_dir)
            profile = get_domain_by_id("biohacking_longevity")

            assert profile is not None
            assert profile.id == "biohacking_longevity"
            assert profile.name == "Biohacking & Longevity"

            # Explicit cleanup to avoid Windows file locks
            json_path.unlink()
            del profile, config_domains, json_path
            gc.collect()
