#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.event_classification import FAILURE_PHRASES, DECISION_PHRASES, METHOD_TAGS  # noqa: E402
from utils.text_utils import chunk_sentences  # noqa: E402


def is_valid_pdf(path: Path) -> bool:
    try:
        with open(path, "rb") as handle:
            return handle.read(5) == b"%PDF-"
    except Exception:
        return False


def has_signal(sentence_l: str) -> bool:
    return (
        any(p in sentence_l for lst in FAILURE_PHRASES.values() for p in lst)
        or any(p in sentence_l for lst in DECISION_PHRASES.values() for p in lst)
        or any(p in sentence_l for lst in METHOD_TAGS.values() for p in lst)
    )


def scan_cache(cache_dir: Path) -> None:
    pdfs = sorted(cache_dir.glob("*.pdf"))
    results: list[dict[str, object]] = []
    summary = Counter()

    for pdf_path in pdfs:
        print(f"[{len(results) + 1}/{len(pdfs)}] {pdf_path.name}", flush=True)
        info = {
            "file": pdf_path.name,
            "valid": is_valid_pdf(pdf_path),
            "pages": 0,
            "text_pages": 0,
            "chars": 0,
            "sentences": 0,
            "signals": 0,
            "error": None,
        }

        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                info["pages"] = len(pdf.pages)
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if not text.strip():
                        continue
                    info["text_pages"] += 1
                    info["chars"] += len(text)
                    sentences = chunk_sentences(text)
                    info["sentences"] += len(sentences)
                    info["signals"] += sum(1 for sentence in sentences if has_signal(sentence.lower()))
        except (OSError, IOError, PDFSyntaxError) as exc:
            info["error"] = f"{type(exc).__name__}: {exc}"

        results.append(info)

    summary["total"] = len(results)
    summary["valid"] = sum(1 for row in results if row["valid"])
    summary["invalid"] = sum(1 for row in results if not row["valid"])
    summary["with_text"] = sum(1 for row in results if row["text_pages"])
    summary["without_text"] = sum(1 for row in results if not row["text_pages"])
    summary["signal_positive"] = sum(1 for row in results if row["signals"])
    summary["signal_free"] = sum(1 for row in results if not row["signals"])
    summary["errors"] = sum(1 for row in results if row["error"])

    print("SUMMARY")
    for key in [
        "total",
        "valid",
        "invalid",
        "with_text",
        "without_text",
        "signal_positive",
        "signal_free",
        "errors",
    ]:
        print(f"{key}: {summary[key]}", flush=True)

    print("\nHIGH-VALUE FILES")
    for row in sorted(
        [row for row in results if row["signals"] > 0],
        key=lambda row: (-row["signals"], -row["chars"], str(row["file"])),
    )[:15]:
        print(
            f"{row['signals']:>4} signals | {row['sentences']:>4} sentences | "
            f"{row['text_pages']:>2}/{row['pages']:>2} text/pages | {row['file']}"
        , flush=True)

    print("\nDEAD WEIGHT CANDIDATES")
    for row in sorted(
        [row for row in results if row["signals"] == 0],
        key=lambda row: (row["text_pages"], row["chars"], str(row["file"])),
    )[:20]:
        status = "INVALID" if not row["valid"] else "OK"
        print(
            f"{status:7} | text_pages={row['text_pages']:>2} | chars={row['chars']:>6} | {row['file']}"
        , flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan an RSS PDF cache and summarize the results")
    parser.add_argument("cache_dir", nargs="?", default=None, help="Path to the RSS cache directory")
    parser.add_argument("--cache-dir", dest="cache_dir_flag", default=None, help="Path to the RSS cache directory")
    args = parser.parse_args(argv)

    cache_dir = args.cache_dir_flag or args.cache_dir or "data/cache/rss"
    scan_cache(Path(cache_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())