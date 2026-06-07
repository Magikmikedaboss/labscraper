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
    text = report_path.read_text(encoding="utf-16")
    start = text.find("{")
    data, _ = json.JSONDecoder().raw_decode(text[start:])
    for vuln in data.get("vulnerabilities", [])[:10]:
        print(
            f"Safety {vuln.get('package_name')} {vuln.get('analyzed_version')} "
            f"{vuln.get('vulnerable_spec')}"
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