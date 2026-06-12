from __future__ import annotations

import json
import logging
import sys
from pathlib import Path


logger = logging.getLogger(__name__)


def summarize_bandit(report_path: Path) -> None:
    raw = report_path.read_bytes()

    text = None
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
        try:
            text = raw.decode(encoding)
            logger.debug("Decoded %s using %s", report_path, encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        logger.error("Failed to decode %s with utf-8, utf-8-sig, utf-16, or latin-1", report_path)
        raise ValueError(f"Could not decode {report_path}")

    data = json.loads(text)
    results = data.get("results", []) if isinstance(data, dict) else []
    for issue in results[:10]:
        if not isinstance(issue, dict):
            continue
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
            logger.debug("Decoded %s using %s", report_path, encoding)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        logger.error("Failed to decode %s with utf-8, utf-8-sig, utf-16, or latin-1", report_path)
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
        print("Usage: summarize_security_report.py <report-path> <bandit|safety>", file=sys.stderr)
        return 2

    report_path = Path(argv[1])
    report_type = argv[2]

    if not report_path.exists():
        logger.error("Report file not found: %s", report_path)
        print(f"Report file not found: {report_path}", file=sys.stderr)
        return 1

    try:
        if report_type == "bandit":
            summarize_bandit(report_path)
        elif report_type == "safety":
            summarize_safety(report_path)
        else:
            print(f"Unknown report type: {report_type}", file=sys.stderr)
            return 2
    except Exception as exc:
        print(f"Failed to summarize {report_path.name}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
