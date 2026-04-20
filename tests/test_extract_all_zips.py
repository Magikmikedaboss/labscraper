import zipfile
from tools.extract_all_zips import extract_all_zips

def test_extract_all_zips_blocks_path_traversal(tmp_path):
    zip_path = tmp_path / "malicious.zip"
    # Create a zip with a member that tries to escape the extraction root
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../escaped.txt", "malicious data")
    failures = extract_all_zips(str(tmp_path))
    # Should report an unsafe member with reason == "unsafe member" and member containing "../escaped.txt"
    assert any(f.get("reason") == "unsafe member" and "../escaped.txt" in f.get("member", "") for f in failures)
    # The file should not exist outside the extraction root
    escaped_path = tmp_path.parent / "escaped.txt"
    assert not escaped_path.exists()


def test_extract_all_zips_with_good_zip(tmp_path):
    zip_path = tmp_path / "test.zip"
    # Create a separate directory for the file to be zipped
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    testfile = src_dir / "f.txt"
    known_content = "extracted-data"
    testfile.write_text(known_content)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(testfile, arcname="f.txt")
    # Remove the original file before extraction to ensure it must be extracted
    testfile.unlink()
    failures = extract_all_zips(str(tmp_path))
    assert failures == []
    # Check that the extracted file exists at the expected location and has the correct content
    extracted_file = tmp_path / "f.txt"
    assert extracted_file.exists()
    assert extracted_file.read_text() == known_content

def test_extract_all_zips_with_invalid_zip(tmp_path):
    fake_zip = tmp_path / "bad.zip"
    fake_zip.write_text("not a zip")
    failures = extract_all_zips(str(tmp_path))
    assert any(f.get("zip_path") == str(fake_zip) for f in failures)
