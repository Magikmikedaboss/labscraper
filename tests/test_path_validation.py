import pytest

from utils.path_validation import validate_domain_id


def test_validate_domain_id_accepts_safe_value():
    assert validate_domain_id("construction_science") == "construction_science"


@pytest.mark.parametrize(
    "domain_id,expected_message",
    [
        ("../etc/passwd", "traversal"),
        ("some/domain", "path separators"),
        ("some\\domain", "path separators"),
        ("", "non-empty string"),
        ("domain$name!", "only letters"),
    ],
)
def test_validate_domain_id_rejects_unsafe_inputs(domain_id, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        validate_domain_id(domain_id)


def test_validate_domain_id_rejects_absolute_path():
    with pytest.raises(ValueError, match="path separators"):
        validate_domain_id("C:/windows/system32")
