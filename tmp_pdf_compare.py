from __future__ import annotations

import argparse
import re
from pathlib import Path
from difflib import SequenceMatcher

from pdfminer.pdfparser import PDFSyntaxError
import pdfplumber

DEFAULT_PDF_PATHS = [
    Path('cache/rss/d558418180cd10045eab4512f65efc4f1dff78fb863d5131b3b14c1c684b91ba.pdf'),
    Path('cache/rss/651d057955a5c730db38440bf8070a4c.pdf'),
]

word_re = re.compile(r"[\w\-']+", re.UNICODE)
sentence_re = re.compile(r'(?<=[.!?])\s+')


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two PDFs extracted from the RSS cache")
    parser.add_argument("pdf_paths", nargs="*", help="Paths to two PDF files to compare")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf_paths = [Path(path) for path in args.pdf_paths] if args.pdf_paths else DEFAULT_PDF_PATHS
    if len(pdf_paths) != 2:
        print("ERROR: provide exactly two PDF paths, or omit arguments to use the default pair.")
        return 1

    records = []
    for path in pdf_paths:
        try:
            with pdfplumber.open(str(path)) as pdf:
                meta = pdf.metadata or {}
                texts = []
                for page in pdf.pages:
                    texts.append(page.extract_text() or "")
                full_text = "\n".join(texts)
                words = word_re.findall(full_text)
                sentences = [s.strip() for s in sentence_re.split(full_text.replace("\n", " ")) if s.strip()]
                records.append(
                    {
                        "name": path.name,
                        "title": meta.get("Title") or meta.get("title") or "",
                        "pages": len(pdf.pages),
                        "word_count": len(words),
                        "sentence_count": len(sentences),
                        "normalized_text": normalize_text(full_text),
                        "sentences": sentences,
                    }
                )
        except (FileNotFoundError, OSError, PDFSyntaxError, Exception) as exc:
            records.append({"name": path.name, "error": str(exc)})
            print(f"ERROR {path.name}: {exc}")
            continue

    if len(records) != 2 or any("error" in record for record in records):
        return 0

    left, right = records
    text_similarity = SequenceMatcher(None, left["normalized_text"], right["normalized_text"]).ratio()
    sentences_similarity = SequenceMatcher(None, " ".join(left["sentences"][:500]), " ".join(right["sentences"][:500])).ratio()

    print(f"LEFT title={left['title'] or '[none]'}")
    print(f"LEFT pages={left['pages']} words={left['word_count']} sentences={left['sentence_count']}")
    print(f"RIGHT title={right['title'] or '[none]'}")
    print(f"RIGHT pages={right['pages']} words={right['word_count']} sentences={right['sentence_count']}")
    print(f"TEXT_SIMILARITY={text_similarity:.2%}")
    print(f"HEAD_SENTENCE_SIMILARITY={sentences_similarity:.2%}")
    print()
    print("LEFT_FIRST_5")
    for sentence in left["sentences"][:5]:
        print(sentence[:220])
    print()
    print("RIGHT_FIRST_5")
    for sentence in right["sentences"][:5]:
        print(sentence[:220])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
