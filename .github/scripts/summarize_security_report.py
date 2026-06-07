from __future__ import annotations

import json
import sys
from pathlib import Path


def summarize_bandit(report_path: Path) -> None:
    data = json.loads(report_path.read_text(encoding="utf-8"))
    for issue in data.get("results", [])[:10]:
        print(
            f"Bandit {issue.get('test_id')} {issue.get('issue_text')} "
            f"({issue.get('filename')}:{issue.get('line_number')})"
        )


def summarize_safety(report_path: Path) -> None:
    raw = report_path.read_bytes()

    text = None
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ValueError(f"Could not decode {report_path}")

    text = text.strip()
    if not text:
        raise ValueError("Safety report is empty")

    parsed = json.loads(text)
    if isinstance(parsed, dict):
        data = parsed
    elif isinstance(parsed, list):
        data = {"vulnerabilities": parsed}
    else:
        raise ValueError("Safety report JSON must be an object or array")

    vulnerabilities = data.get("vulnerabilities", [])

    for vuln in vulnerabilities[:10]:
        if not isinstance(vuln, dict):
            continue
        print(
            f"Safety {vuln.get('package_name')} "
            f"{vuln.get('analyzed_version') or vuln.get('installed_version')} "
            f"{vuln.get('vulnerable_spec') or vuln.get('specifier', '')}"
        )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: summarize_security_report.py <report-path> <bandit|safety>")
        return 2

    report_path = Path(argv[1])
    report_type = argv[2]

    if not report_path.exists():
        return 0

    try:
        if report_type == "bandit":
            summarize_bandit(report_path)
        elif report_type == "safety":
            summarize_safety(report_path)
        else:
            print(f"Unknown report type: {report_type}")
            return 2
    except Exception as exc:
        print(f"Failed to summarize {report_path.name}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))