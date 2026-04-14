"""Tests for input and feed configuration validation helpers."""


import pytest

from utils.validators import (
    ValidationError,
    validate_batch_size,
    validate_database,
    validate_directory,
    validate_domain_name,
    validate_feed_config,
    validate_feed_url,
    validate_file_path,
    validate_input_pdfs_directory,
    validate_memory_limit,
    validate_output_path,
    validate_percentage,
    validate_positive_integer,
    validate_search_terms,
)


def test_validate_directory_and_file_paths(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config_file = data_dir / "config.json"
    config_file.write_text("{}", encoding="utf-8")

    assert validate_directory(data_dir) == data_dir
    assert validate_directory(tmp_path / "new_dir", must_exist=False) == tmp_path / "new_dir"
    assert validate_file_path(config_file) == config_file

    with pytest.raises(ValidationError):
        validate_directory(config_file)

    with pytest.raises(ValidationError):
        validate_file_path(data_dir)


def test_validate_database_accepts_new_sqlite_paths(tmp_path):
    db_path = tmp_path / "nested" / "runs.sqlite"
    validated = validate_database(db_path, must_exist=False)

    assert validated == db_path
    assert db_path.parent.exists()

    with pytest.raises(ValidationError):
        validate_database(tmp_path / "runs.txt", must_exist=False)

    with pytest.raises(ValidationError):
        validate_database(tmp_path / "missing.sqlite", must_exist=True)


def test_validate_feed_url_and_domain_name():
    assert validate_feed_url("https://example.com/feed.xml") == "https://example.com/feed.xml"
    assert validate_domain_name("Construction_Science") == "construction_science"

    with pytest.raises(ValidationError):
        validate_feed_url("ftp://example.com/feed.xml")

    with pytest.raises(ValidationError):
        validate_domain_name("bad domain!")


def test_validate_input_pdfs_directory_and_output_path(tmp_path):
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()

    with pytest.raises(ValidationError):
        validate_input_pdfs_directory(pdf_dir)

    (pdf_dir / "paper.pdf").write_bytes(b"%PDF-1.4\n")
    assert validate_input_pdfs_directory(pdf_dir) == pdf_dir

    output_path = tmp_path / "exports" / "results.csv"
    validated = validate_output_path(output_path)
    assert validated == output_path
    assert output_path.parent.exists()


def test_validate_numeric_helpers_and_search_terms():
    assert validate_positive_integer("5", "workers") == 5
    assert validate_percentage("0.5") == 0.5
    assert validate_search_terms([" Foo ", "BAR"]) == ["foo", "bar"]
    assert validate_batch_size("10") == 10
    assert validate_memory_limit("1.5GB") == 1500
    assert validate_memory_limit(512) == 512

    with pytest.raises(ValidationError):
        validate_positive_integer("abc")

    with pytest.raises(ValidationError):
        validate_percentage("1.5")

    with pytest.raises(ValidationError):
        validate_search_terms(["valid", ""])

    with pytest.raises(ValidationError):
        validate_batch_size(1001)

    with pytest.raises(ValidationError):
        validate_memory_limit("bad-format")

    with pytest.raises(ValidationError):
        validate_memory_limit(50)


def test_validate_feed_config_accepts_valid_entries():
    config = {
        "feeds": [
            {
                "name": "Materials Feed",
                "url": "https://example.com/materials.xml",
                "domain": "construction_science",
                "enabled": True,
                "keywords": ["concrete", "steel"],
            },
            {
                "name": "General Feed",
                "url": "http://example.org/general.xml",
                "enabled": False,
                "notes": "Optional metadata",
            },
        ]
    }

    validated = validate_feed_config(config)

    assert len(validated["feeds"]) == 2
    assert validated["feeds"][0]["domain"] == "construction_science"
    assert validated["feeds"][1]["enabled"] is False
    assert validated["feeds"][1]["notes"] == "Optional metadata"


def test_validate_feed_config_rejects_invalid_structure():
    with pytest.raises(ValidationError):
        validate_feed_config(["not", "a", "dict"])

    with pytest.raises(ValidationError):
        validate_feed_config({"feeds": {"bad": "type"}})

    with pytest.raises(ValidationError):
        validate_feed_config({"feeds": [{"name": "Missing URL"}]})
