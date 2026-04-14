import zipfile
import os
from pathlib import Path

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
                                continue
                            if member.is_dir():
                                abs_target.mkdir(parents=True, exist_ok=True)
                            else:
                                abs_target.parent.mkdir(parents=True, exist_ok=True)
                                with abs_target.open('wb') as f:
                                    f.write(zip_ref.read(member))
                except zipfile.BadZipFile as e:
                    print(f"  ⚠️  Bad zip file {zip_path}: {e}")
                    failures.append(zip_path)
                except Exception as e:
                    print(f"  ⚠️  Failed to extract {zip_path}: {e}")
                    failures.append(zip_path)
    return failures

if __name__ == "__main__":
    failures = extract_all_zips("input/pdfs")
    if failures:
        print(f"❌ Extraction failed for {len(failures)} zip file(s): {failures}")
        import sys
        sys.exit(1)
    print("✅ All zip files extracted.")
