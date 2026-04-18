import zipfile
from tools.extract_all_zips import extract_all_zips


def test_extract_all_zips_with_good_zip(tmp_path):
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        testfile = tmp_path / "f.txt"
        testfile.write_text("data")
        zf.write(testfile, arcname="f.txt")
    failures = extract_all_zips(str(tmp_path))
    assert failures == []

def test_extract_all_zips_with_invalid_zip(tmp_path):
    fake_zip = tmp_path / "bad.zip"
    fake_zip.write_text("not a zip")
    failures = extract_all_zips(str(tmp_path))
    assert fake_zip in failures or any(str(fake_zip) in str(f) for f in failures)
