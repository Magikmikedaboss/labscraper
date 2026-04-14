import zipfile
import os
from pathlib import Path

# Recursively find all zip files in the workspace
def extract_all_zips(base_dir):
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith('.zip'):
                zip_path = Path(root) / file
                print(f"Extracting: {zip_path}")
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(Path(root))
                except Exception as e:
                    print(f"  ⚠️  Failed to extract {zip_path}: {e}")

if __name__ == "__main__":
    extract_all_zips("input/pdfs")
    print("✅ All zip files extracted.")
