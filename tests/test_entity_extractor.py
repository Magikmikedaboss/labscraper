from utils.entity_extractor import load_text_seed_file
from utils.entities import normalize_name


def test_load_text_seed_file_strips_comments(tmp_path):
    seed_file = tmp_path / "compounds.txt"
    seed_file.write_text("rapamycin  # synonym\n# monoclonal antibodies\nmetformin\n", encoding="utf-8")

    assert load_text_seed_file(seed_file) == ["rapamycin", "metformin"]


def test_normalize_name_preserve_spaces_flag_controls_whitespace():
    assert normalize_name("  HeLa  cells  ", preserve_spaces=True) == "hela cells"
    assert normalize_name("  HeLa  cells  ") == "helacells"