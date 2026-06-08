"""Helpers for collecting abstract/article text from feed entries and article pages."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import requests

from utils.feed_utils import USER_AGENT


_ABSTRACT_LINK_PATTERNS = (
    re.compile(r"https?://(?:dx\.)?doi\.org/[^\s<>\"']+", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?ascelibrary\.org/[^\s<>\"']+", re.IGNORECASE),
    re.compile(r"https?://arxiv\.org/abs/[^\s<>\"']+", re.IGNORECASE),
)


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _is_candidate_abstract_link(href: str) -> bool:
    parsed = urlparse(href)
    hostname = (parsed.hostname or "").lower()
    path = parsed.path or ""

    if hostname == "doi.org" or hostname.endswith(".doi.org"):
        return True

    if hostname == "ascelibrary.org" or hostname.endswith(".ascelibrary.org"):
        return True

    if (hostname == "arxiv.org" or hostname.endswith(".arxiv.org")) and path.startswith("/abs/"):
        return True

    return False


class _AbstractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._candidate_stack: list[tuple[str, list[str]]] = []
        self._candidates: list[str] = []
        self._heading_tag: str | None = None
        self._heading_buffer: list[str] = []
        self._capture_next_paragraph = False

    @staticmethod
    def _is_target_container(tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag not in {"div", "p"}:
            return False

        attr_map = {key.lower(): (value or "") for key, value in attrs}
        classes = {part for part in re.split(r"\s+", attr_map.get("class", "").lower()) if part}
        return "abstract" in classes or "abstractsection" in classes or attr_map.get("id", "").lower() == "abstract"

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if self._capture_next_paragraph and tag == "p":
            self._candidate_stack.append((tag, []))
            self._capture_next_paragraph = False
            return

        if self._is_target_container(tag, attrs):
            self._candidate_stack.append((tag, []))
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_tag = tag
            self._heading_buffer = []

    def handle_data(self, data: str) -> None:
        if self._heading_tag is not None:
            self._heading_buffer.append(data)
        if self._candidate_stack:
            self._candidate_stack[-1][1].append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._heading_tag == tag:
            heading_text = _normalize_whitespace("".join(self._heading_buffer)).lower()
            if heading_text == "abstract":
                self._capture_next_paragraph = True
            self._heading_tag = None
            self._heading_buffer = []

        if self._candidate_stack and self._candidate_stack[-1][0] == tag:
            _, buffer = self._candidate_stack.pop()
            abstract_text = _normalize_whitespace("".join(buffer))
            if len(abstract_text) > 50:
                self._candidates.append(abstract_text)

    def get_candidates(self) -> list[str]:
        return self._candidates


def find_abstract_links(entry: dict[str, Any]) -> list[str]:
    """Return candidate abstract/article URLs from a feed entry."""
    candidates: list[str] = []

    entry_link = str(entry.get("link", "") or "")
    if entry_link:
        candidates.append(entry_link)

    for link in entry.get("links", []):
        href = str(link.get("href", "") or "")
        if not href:
            continue
        if _is_candidate_abstract_link(href):
            candidates.append(href)

    for blob in [entry.get("summary", ""), *[content.get("value", "") for content in entry.get("content", [])]]:
        text = str(blob or "")
        if not text:
            continue
        for pattern in _ABSTRACT_LINK_PATTERNS:
            candidates.extend(pattern.findall(text))

    return list(dict.fromkeys(candidates))


def extract_abstract_text_from_html(html: str) -> str | None:
    """Extract abstract text from article HTML when available."""
    parser = _AbstractParser()
    parser.feed(html)
    for abstract_text in parser.get_candidates():
        if len(abstract_text) > 50:
            return abstract_text
    return None


def extract_abstract_text_from_url(url: str, timeout: int = 30) -> str | None:
    """Fetch an article page and extract its abstract text if present."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return None
    return extract_abstract_text_from_html(response.text)


__all__ = [
    "find_abstract_links",
    "extract_abstract_text_from_html",
    "extract_abstract_text_from_url",
]
