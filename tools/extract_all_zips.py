
import zipfile
import os
import sys
import shutil
from pathlib import Path
import datetime

# Recursively find all zip files in the workspace
def extract_all_zips(base_dir):
    failures = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith('.zip'):
                zip_path = Path(root) / file
                print(f"Extracting: {zip_path}")
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        for member in zip_ref.infolist():
                            member_path = Path(root) / member.filename
                            abs_target = member_path.resolve()
                            abs_root = Path(root).resolve()
                            try:
                                abs_target.relative_to(abs_root)
                            except ValueError:
                                print(f"  ⚠️  Skipping unsafe file in {zip_path}: {member.filename}")
                                failures.append({
                                    "zip_path": str(zip_path),
                                    "member": member.filename,
                                    "reason": "unsafe member"
                                })
                                continue
                            mode = (member.external_attr >> 16) & 0o777
                            # Convert member.date_time to POSIX timestamp
                            try:
                                dt = datetime.datetime(*member.date_time, tzinfo=datetime.timezone.utc)
                                timestamp = dt.timestamp()
                            except Exception:
                                timestamp = None
                            if member.is_dir():
                                abs_target.mkdir(parents=True, exist_ok=True)
                            else:
                                abs_target.parent.mkdir(parents=True, exist_ok=True)
                                with zip_ref.open(member) as src, abs_target.open('wb') as dst:
                                    shutil.copyfileobj(src, dst, length=64 * 1024)
                            # Set permissions and timestamps for both files and directories
                            if mode:
                                os.chmod(abs_target, mode)
                            if timestamp is not None:
                                os.utime(abs_target, (timestamp, timestamp))
                except zipfile.BadZipFile as e:
                    print(f"  ⚠️  Bad zip file {zip_path}: {e}")
                    failures.append({
                        "zip_path": str(zip_path),
                        "member": None,
                        "reason": "bad_zip",
                        "error": str(e)
                    })
                except Exception as e:
                    print(f"  ⚠️  Failed to extract {zip_path}: {e}")
                    failures.append({
                        "zip_path": str(zip_path),
                        "member": None,
                        "reason": "error",
                        "error": str(e)
                    })
    return failures

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all zip files in a directory tree.")
    parser.add_argument(
        "-d", "--directory",
        type=str,
        default="input/pdfs",
        help="Base directory to search for zip files (default: input/pdfs)"
    )
    args = parser.parse_args()
    base_dir = args.directory
    if not os.path.isdir(base_dir):
        print(f"❌ Directory does not exist: {base_dir}")
        sys.exit(1)
    failures = extract_all_zips(base_dir)
    if failures:
        print(f"❌ Extraction failed for {len(failures)} zip file(s): {failures}")
        sys.exit(1)
    print("✅ All zip files extracted.")
