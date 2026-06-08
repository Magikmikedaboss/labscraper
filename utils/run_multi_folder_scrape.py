"""
Multi-Folder Scraper
Run the scraper against multiple PDF folders and combine results into one database
"""

import logging
import os
import subprocess  # nosec B404 - controlled local scraper invocation
import sys
from pathlib import Path


logger = logging.getLogger(__name__)

def run_scraper(input_dir: str, domain: str, output_db: str):
    """Run scraper on a specific folder"""
    print(f"\n{'='*70}")
    print(f"SCRAPING: {input_dir}")
    print(f"Domain: {domain}")
    print(f"Database: {output_db}")
    print(f"{'='*70}\n")
    
    script_dir = Path(__file__).resolve().parent
    script_path = script_dir / "scrape_pdfs_phase1.py"
    if not script_path.exists():
        print(f"❌ Error: Script not found at {script_path}")
        raise FileNotFoundError(f"Script not found: {script_path}")

    cmd = [
        sys.executable,
        str(script_path),
        "--domain", domain,
        "--input-dir", input_dir,
        "--output-db", output_db
    ]

    timeout_seconds = 600  # 10 minutes, adjust as needed
    try:
        result = subprocess.run(cmd, capture_output=False, timeout=timeout_seconds)  # nosec B603 - command is built from a local script path and explicit args
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: Scraper timed out after {timeout_seconds} seconds for {input_dir}")
        return 1  # Non-zero status for timeout

    if result.returncode != 0:
        print(f"⚠️  Warning: Scraper returned non-zero exit code for {input_dir}")

    return result.returncode


def validate_configs(configs: list[dict[str, str]]) -> None:
    for config in configs:
        input_raw = config.get("input_dir", "")
        output_raw = config.get("output_db", "")
        domain = config.get("domain", "(unknown domain)")

        missing_fields = [key for key, value in (("input_dir", input_raw), ("output_db", output_raw)) if not value]
        if missing_fields:
            message = f"ERROR: Invalid config for domain '{domain}': missing or empty fields: {', '.join(missing_fields)}"
            print(message)
            logger.error("Invalid config for domain '%s': missing or empty fields: %s", domain, ", ".join(missing_fields))
            sys.exit(1)

        input_dir = Path(input_raw).expanduser()
        output_db = Path(output_raw).expanduser()

        if not input_dir.exists() or not input_dir.is_dir():
            print(f"ERROR: Invalid config for domain '{domain}': input_dir does not exist or is not a directory: {input_dir}")
            logger.error("Invalid config for domain '%s': input_dir does not exist or is not a directory: %s", domain, input_dir)
            sys.exit(1)

        output_parent = output_db.parent
        if not output_parent.exists() or not output_parent.is_dir():
            print(f"ERROR: Invalid config for domain '{domain}': output_db parent directory does not exist or is not a directory: {output_parent}")
            logger.error("Invalid config for domain '%s': output_db parent directory does not exist or is not a directory: %s", domain, output_parent)
            sys.exit(1)

        if not os.access(output_parent, os.W_OK):
            print(f"ERROR: Invalid config for domain '{domain}': output_db parent directory is not writable: {output_parent}")
            logger.error("Invalid config for domain '%s': output_db parent directory is not writable: %s", domain, output_parent)
            sys.exit(1)


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
            "input_dir": "input/pdfs/biohacking_longevity",
            "domain": "biohacking_longevity",
            "output_db": "output/combined_biohacking.sqlite"
        },
        {
            "input_dir": "input/pdfs/neuroscience_cognition",
            "domain": "neuroscience_cognition",
            "output_db": "output/combined_biohacking.sqlite"  # Same DB = combined!
        },
    ]

    validate_configs(configs)
    
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
        status = "✅ Success" if success == 0 else "❌ Failed"
        print(f"  {status}: {folder}")

    if configs:
        # Collect unique output DBs and their associated domains
        db_to_domains = {}
        for config in configs:
            db = config.get('output_db')
            domain = config.get('domain')
            if db:
                db_to_domains.setdefault(db, set()).add(domain)

        print("\n📊 Output databases:")
        for db, domains in db_to_domains.items():
            print(f"  - {db} (domains: {', '.join(sorted(domains))})")

        print("\nNext steps:")
        print("  1. Run dual-lens export for each output database:")
        for db, domains in db_to_domains.items():
            for domain in sorted(domains):
                print(f"     python export_dual_lens.py {db} {domain}")
        print("  2. Analyze results in CSV files")
    else:
        print("\nNo configs available to show output databases or next steps.")


if __name__ == "__main__":
    main()
