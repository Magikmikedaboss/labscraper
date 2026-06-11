import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(r"c:\projects\labscraper")
CONFIG = ROOT / "config" / "feeds.json"
TMP = ROOT / "tmp" / "one_feed_scan.json"

cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
feeds = [
    feed
    for feed in cfg["feeds"]
    if feed.get("enabled", True) and feed.get("domain") == "construction_science"
]

print(f"Scanning {len(feeds)} construction feeds one at a time...")
for feed in feeds:
    TMP.write_text(json.dumps({"feeds": [feed]}, indent=2), encoding="utf-8")
    print("\n" + "=" * 80)
    print(f"FEED: {feed.get('name')}")
    print("=" * 80)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "test_feeds.py"),
            "--config",
            str(TMP),
            "--default-domain",
            "construction_science",
        ],
        check=False,
    )
