"""HTML and archive page collectors for site-specific construction science sources."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
import ipaddress
import logging
import socket
from time import monotonic
from urllib.parse import urljoin, urlparse

import requests

from utils.feed_utils import USER_AGENT


logger = logging.getLogger(__name__)


_SKIP_TAGS = {"script", "style", "noscript", "svg"}
_ASSET_EXTENSIONS = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".map",
    ".pdf",
    ".png",
    ".svg",
    ".webp",
    ".zip",
}
_MAX_FETCH_BYTES = 10 * 1024 * 1024
_BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata",
    "metadata.google.internal",
    "instance-data",
    "instance-data.local",
}
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._text_parts: list[str] = []
        self.links: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        attr_map = dict(attrs)
        href = attr_map.get("href")
        if tag in {"a", "iframe", "source", "link"} and href:
            self.links.append(href)
        src = attr_map.get("src")
        if tag in {"iframe", "source", "embed"} and src:
            self.links.append(src)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        else:
            self._text_parts.append(text)

    def get_text(self) -> str:
        return " ".join(self._text_parts)

    def get_title(self) -> str:
        return " ".join(self.title_parts).strip()


@dataclass(frozen=True)
class CollectedDocument:
    url: str
    title: str
    text: str


def _is_same_domain(base_url: str, candidate_url: str) -> bool:
    base = urlparse(base_url)
    candidate = urlparse(candidate_url)
    return bool(candidate.netloc) and candidate.netloc.lower() == base.netloc.lower()


def _is_probably_html_link(url: str) -> bool:
    parsed = urlparse(url)
    path = (parsed.path or "").lower()
    return not any(path.endswith(ext) for ext in _ASSET_EXTENSIONS)


def _normalize_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href) if href else ""


def _is_blocked_ip(address: str) -> bool:
    try:
        ip_address = ipaddress.ip_address(address)
    except ValueError:
        return True

    if any(ip_address in network for network in _BLOCKED_NETWORKS):
        return True

    return (
        ip_address.is_private
        or ip_address.is_loopback
        or ip_address.is_link_local
        or ip_address.is_multicast
        or ip_address.is_unspecified
        or ip_address.is_reserved
    )


def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    hostname = parsed.hostname.strip().lower().rstrip(".")
    if hostname in _BLOCKED_HOSTNAMES or hostname.endswith(".localhost"):
        return False

    try:
        resolved = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    resolved_addresses = {entry[4][0] for entry in resolved if entry and entry[4]}
    if not resolved_addresses:
        return False

    return all(not _is_blocked_ip(address) for address in resolved_addresses)


def _extract_page(parser_source: str) -> tuple[str, list[str], str]:
    parser = _PageParser()
    parser.feed(parser_source)
    return parser.get_title(), parser.links, parser.get_text()


def fetch_page(url: str, timeout: int = 20) -> str:
    normalized_url = url.strip()
    if not _is_safe_url(normalized_url):
        raise ValueError(f"Unsafe or unsupported URL blocked: {normalized_url}")

    headers = {"User-Agent": USER_AGENT}
    current_url = normalized_url
    for _ in range(5):
        if not _is_safe_url(current_url):
            raise ValueError(f"Unsafe URL blocked: {current_url}")

        with requests.get(current_url, timeout=timeout, headers=headers, stream=True, allow_redirects=False) as response:
            response.raise_for_status()

            if 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if not location:
                    raise ValueError(f"Redirect missing Location header: {current_url}")
                stripped_location = location.strip()
                current_url = urljoin(current_url, stripped_location)
                continue

            if not _is_safe_url(response.url):
                raise ValueError(f"Unsafe redirected URL blocked: {response.url}")

            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    content_length_value = int(content_length)
                except ValueError:
                    content_length_value = None
                if content_length_value is not None and content_length_value > _MAX_FETCH_BYTES:
                    raise ValueError(f"Response too large: {content_length_value} bytes")

            body = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                body.extend(chunk)
                if len(body) > _MAX_FETCH_BYTES:
                    raise ValueError(f"Response exceeded {_MAX_FETCH_BYTES} bytes")

            encoding = response.encoding or response.apparent_encoding or "utf-8"
            return body.decode(encoding, errors="replace")

    raise ValueError(f"Too many redirects for URL: {normalized_url}")


def collect_documents(
    start_url: str,
    max_pages: int = 20,
    same_domain_only: bool = True,
    same_path_prefix: str | None = None,
    max_depth: int = 1,
    request_timeout: int = 20,
    max_seconds: int = 60,
) -> list[CollectedDocument]:
    """Collect a small set of HTML documents reachable from a site landing page."""
    if not start_url:
        return []

    normalized_path_prefix = same_path_prefix.strip() if same_path_prefix else None
    if normalized_path_prefix and not normalized_path_prefix.startswith("/"):
        normalized_path_prefix = f"/{normalized_path_prefix}"
    if normalized_path_prefix == "/":
        normalized_path_prefix = None
    if normalized_path_prefix:
        normalized_path_prefix = normalized_path_prefix.rstrip("/") + "/"

    collected: list[CollectedDocument] = []
    seen_urls: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    deadline = monotonic() + max_seconds if max_seconds and max_seconds > 0 else None

    while queue and len(collected) < max_pages:
        if deadline is not None and monotonic() >= deadline:
            break
        current_url, depth = queue.popleft()
        if current_url in seen_urls:
            continue
        seen_urls.add(current_url)

        try:
            html = fetch_page(current_url, timeout=request_timeout)
        except Exception:
            logger.exception("Failed to fetch page %s with timeout=%s", current_url, request_timeout)
            continue

        title, raw_links, text = _extract_page(html)
        cleaned_text = " ".join(text.split())
        if cleaned_text:
            collected.append(CollectedDocument(url=current_url, title=title or current_url, text=cleaned_text))

        if depth >= max_depth:
            continue

        for raw_link in raw_links:
            candidate_url = _normalize_url(current_url, raw_link).strip()
            if not candidate_url or candidate_url in seen_urls:
                continue
            normalized_candidate_url = candidate_url.lower()
            if normalized_candidate_url.startswith(("mailto:", "tel:", "javascript:", "data:")) or candidate_url.startswith("#"):
                continue
            if not _is_probably_html_link(candidate_url):
                continue
            if same_domain_only and not _is_same_domain(start_url, candidate_url):
                continue
            if normalized_path_prefix:
                candidate_path = (urlparse(candidate_url).path or "").rstrip("/") + "/"
                if not candidate_path.startswith(normalized_path_prefix):
                    continue
            queue.append((candidate_url, depth + 1))

    return collected[:max_pages]


def extract_pdf_links_from_page(url: str, timeout: int = 20) -> list[str]:
    """Extract PDF URLs from a landing page, including iframe-based wrappers."""
    try:
        html = fetch_page(url, timeout=timeout)
    except Exception:
        logger.exception("fetch_page failed for url=%s timeout=%s", url, timeout)
        return []

    _, links, _ = _extract_page(html)
    pdf_links: list[str] = []
    for raw_link in links:
        candidate_url = _normalize_url(url, raw_link)
        if not candidate_url:
            continue
        parsed = urlparse(candidate_url)
        parsed_path = parsed.path.lower()
        query = parsed.query.lower()
        if parsed_path.endswith(".pdf") or ".pdf" in query:
            pdf_links.append(candidate_url)

    return list(dict.fromkeys(pdf_links))