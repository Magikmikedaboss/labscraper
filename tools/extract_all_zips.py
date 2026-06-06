
import logging
import zipfile
import os
import sys
import shutil
from pathlib import Path, PurePosixPath
import datetime
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_FILE_COUNT = 10_000
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB per archive
MAX_UNCOMPRESSED_FILE_SIZE = 512 * 1024 * 1024  # 512 MiB per file
RATIO_THRESHOLD = 1000.0

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
                        total_extracted_bytes = 0
                        extracted_file_count = 0
                        for member in zip_ref.infolist():
                            # Sanitize member.filename
                            orig_name = member.filename
                            p = PurePosixPath(orig_name)
                            # Reject absolute paths, parent components, or empty segments
                            if p.is_absolute() or any(part in ('..', '') for part in p.parts):
                                print(f"  ⚠️  Skipping unsafe file in {zip_path}: {orig_name}")
                                failures.append({
                                    "zip_path": str(zip_path),
                                    "member": orig_name,
                                    "reason": "unsafe member"
                                })
                                continue

                            # Zip-bomb guards
                            if member.file_size > MAX_UNCOMPRESSED_FILE_SIZE:
                                print(f"  ⚠️  Skipping oversized file in {zip_path}: {orig_name}")
                                failures.append({
                                    "zip_path": str(zip_path),
                                    "member": orig_name,
                                    "reason": "file_too_large"
                                })
                                continue

                            if member.compress_size > 0:
                                ratio = member.file_size / member.compress_size
                                if ratio > RATIO_THRESHOLD:
                                    print(f"  ⚠️  Skipping suspicious compression ratio in {zip_path}: {orig_name}")
                                    failures.append({
                                        "zip_path": str(zip_path),
                                        "member": orig_name,
                                        "reason": "suspicious_compression_ratio"
                                    })
                                    continue

                            if not member.is_dir() and extracted_file_count >= MAX_FILE_COUNT:
                                print(f"  ⚠️  Aborting extraction for {zip_path}: max file count exceeded")
                                failures.append({
                                    "zip_path": str(zip_path),
                                    "member": orig_name,
                                    "reason": "max_file_count_exceeded"
                                })
                                break

                            if not member.is_dir() and (total_extracted_bytes + member.file_size) > MAX_TOTAL_BYTES:
                                print(f"  ⚠️  Aborting extraction for {zip_path}: max total bytes exceeded")
                                failures.append({
                                    "zip_path": str(zip_path),
                                    "member": orig_name,
                                    "reason": "max_total_bytes_exceeded"
                                })
                                break

                            sanitized_name = str(p)
                            member_path = Path(root) / sanitized_name
                            abs_target = member_path.resolve()
                            abs_root = Path(root).resolve()
                            try:
                                abs_target.relative_to(abs_root)
                            except ValueError:
                                print(f"  ⚠️  Skipping unsafe file in {zip_path}: {orig_name}")
                                failures.append({
                                    "zip_path": str(zip_path),
                                    "member": orig_name,
                                    "reason": "unsafe member"
                                })
                                continue
                            mode = (member.external_attr >> 16) & 0o777
                            # Convert member.date_time to POSIX timestamp
                            # ZIP stores DOS/local times; offsets may be lost. Interpret as local time.
                            try:
                                dt = datetime.datetime(*member.date_time)  # naive, local time
                                timestamp = time.mktime(dt.timetuple())
                            except Exception as e:
                                logger.warning(
                                    "Failed to parse date_time for zip entry: %r in %s: %r (exception: %r)",
                                    member.filename, zip_path, getattr(member, 'date_time', None), e
                                )
                                timestamp = None
                            if member.is_dir():
                                abs_target.mkdir(parents=True, exist_ok=True)
                            else:
                                abs_target.parent.mkdir(parents=True, exist_ok=True)
                                with zip_ref.open(member) as src, abs_target.open('wb') as dst:
                                    shutil.copyfileobj(src, dst, length=64 * 1024)
                                extracted_file_count += 1
                                total_extracted_bytes += member.file_size
                            # Set permissions and timestamps for both files and directories
                            if mode:
                                try:
                                    if os.name != 'nt':
                                        os.chmod(abs_target, mode)
                                except Exception as e:
                                    print(f"  ⚠️  Could not set permissions for {abs_target}: {e}")
                            if timestamp is not None:
                                try:
                                    os.utime(abs_target, (timestamp, timestamp))
                                except Exception as e:
                                    print(f"  ⚠️  Could not set timestamp for {abs_target}: {e}")
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
        print(f"❌ Extraction failed for {len(failures)} zip file(s). See extract_failures.log for details.")
        import json
        with open("extract_failures.log", "w", encoding="utf-8") as logf:
            json.dump(failures, logf, indent=2, ensure_ascii=False)
        sys.exit(1)
    print("✅ All zip files extracted.")
