"""
Multi-Folder Scraper
Run the scraper against multiple PDF folders and combine results into one database
"""

import subprocess
import sys
from pathlib import Path

def run_scraper(input_dir: str, domain: str, output_db: str):
    """Run scraper on a specific folder"""
    print(f"\n{'='*70}")
    print(f"SCRAPING: {input_dir}")
    print(f"Domain: {domain}")
    print(f"Database: {output_db}")
    print(f"{'='*70}\n")
    
    cmd = [
        sys.executable,
        "scrape_pdfs_phase1.py",
        "--domain", domain,
        "--input-dir", input_dir,
        "--output-db", output_db
    ]
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"⚠️  Warning: Scraper returned non-zero exit code for {input_dir}")
    
    return result.returncode == 0


def main():
    """
    Example: Scrape multiple folders into the same database
    
    This will:
    1. Scrape folder 1 → database
    2. Scrape folder 2 → SAME database (appends)
    3. All data combined in one database
    """
    
    # Configuration
    configs = [
        {
            "input_dir": "input_pdfs/biohacking",
            "domain": "biohacking_longevity",
            "output_db": "output/combined_biohacking.sqlite"
        },
        {
            "input_dir": "input_pdfs/longevity_v1",
            "domain": "biohacking_longevity",
            "output_db": "output/combined_biohacking.sqlite"  # Same DB = combined!
        },
    ]
    
    print("\n" + "="*70)
    print("MULTI-FOLDER SCRAPER")
    print("="*70)
    print(f"\nWill scrape {len(configs)} folders:")
    for i, config in enumerate(configs, 1):
        print(f"  {i}. {config['input_dir']} → {config['output_db']}")
    
    input("\nPress Enter to start...")
    
    # Run each scrape
    results = []
    for config in configs:
        success = run_scraper(
            config["input_dir"],
            config["domain"],
            config["output_db"]
        )
        results.append((config["input_dir"], success))
    
    # Summary
    print("\n" + "="*70)
    print("SCRAPING COMPLETE")
    print("="*70)
    
    for folder, success in results:
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {status}: {folder}")
    
    print(f"\n📊 Combined database: {configs[0]['output_db']}")
    print("\nNext steps:")
    print(f"  1. Run dual-lens export:")
    print(f"     python export_dual_lens.py {configs[0]['output_db']} {configs[0]['domain']}")
    print(f"  2. Analyze results in CSV files")


if __name__ == "__main__":
    main()
