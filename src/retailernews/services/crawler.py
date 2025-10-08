"""High level crawler implementation used by the API and CLI tools."""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from typing import Iterator, List, Sequence, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, HttpUrl

from retailernews.config import SiteConfig
from retailernews.blobstore import DEFAULT_BLOB_ROOT, resolve_blob_root

__all__ = ["Article", "SiteCrawler", "SiteCrawlResult", "crawl"]

BLOB_ROOT = DEFAULT_BLOB_ROOT
EXTRACTED_URLS_INDEX = "extracted_urls.json"
STORED_URLS_INDEX = "stored_urls.json"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    )
}

# Alias used by helper functions for parity with ``src/services`` module.
HEADERS = DEFAULT_HEADERS


def store_json(path: str, payload: dict, *, blob_root: Path | str | None = None) -> None:
    """Save payload as JSON into local blob-style folder."""

    root = resolve_blob_root(blob_root if blob_root is not None else BLOB_ROOT)
    full_path = root / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with full_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def record_stored_url(
    url: str, index_filename: str = STORED_URLS_INDEX, *, blob_root: Path | str | None = None
) -> None:
    """Record a stored article URL inside the blob root index file."""

    root = resolve_blob_root(blob_root if blob_root is not None else BLOB_ROOT)
    root.mkdir(parents=True, exist_ok=True)

    index_path = root / index_filename

    urls: List[str] = []
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            data = None

        if isinstance(data, dict):
            maybe_urls = data.get("urls")
            if isinstance(maybe_urls, list):
                urls = [str(u) for u in maybe_urls]
        elif isinstance(data, list):
            urls = [str(u) for u in data]

    if url in urls:
        return

    urls.append(url)

    with index_path.open("w", encoding="utf-8") as file:
        json.dump({"urls": urls}, file, ensure_ascii=False, indent=2)


def has_been_extracted(
    url: str, index_filename: str = EXTRACTED_URLS_INDEX, *, blob_root: Path | str | None = None
) -> bool:
    """Return True if the given URL has already been extracted."""

    root = resolve_blob_root(blob_root if blob_root is not None else BLOB_ROOT)
    index_path = root / "stored_urls.json"

    # Prefer checking a dedicated index file if present.
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            data = None

        if isinstance(data, dict):
            urls = data.get("urls")
        else:
            urls = data

        if isinstance(urls, list) and url in urls:
            print("The text in the url has already been extracted")
            return True

    if not root.exists():
        return False

    # Fallback: scan all stored JSON payloads for the URL.
    for json_path in root.rglob("*.json"):
        if json_path == index_path:
            continue

        try:
            with json_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(payload, dict) and payload.get("url") == url:
            return True

    return False


def article_path(url: str) -> str:
    """Generate blob-style path based on URL and current date."""

    host = urlparse(url).netloc
    datestamp = datetime.datetime.utcnow().strftime("%Y%m%d")
    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return f"site={host}/{datestamp}/{url_hash}.json"


def extract_text(html: str) -> tuple[str, str]:
    """Extract title and text content from HTML."""

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = soup.get_text("\n", strip=True)
    return title, text


def discover_links_from_page(root_url: str) -> List[str]:
    """Fetch a page and extract same-domain sublinks."""

    response = requests.get(root_url, headers=HEADERS, timeout=(10, 60))
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    parsed_root = urlparse(root_url)
    root_netloc = parsed_root.netloc
    root_path = parsed_root.path.rstrip("/") + "/"

    found: Set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        absolute_url = urljoin(root_url, href)
        parsed = urlparse(absolute_url)

        if parsed.netloc != root_netloc:
            continue
        if not parsed.path.startswith(root_path):
            continue

        found.add(absolute_url.split("#")[0])  # drop fragments
    return list(found)


def discover_links_from_sitemap(
    sitemap_url: str, filter_path: str | None = None
) -> List[str]:
    """Parse sitemap.xml and return links (optionally filtered by path)."""

    response = requests.get(sitemap_url, headers=HEADERS, timeout=(10, 120))
    print(response)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "xml")
    urls = [loc.text for loc in soup.find_all("loc")]
    if filter_path:
        urls = [url for url in urls if filter_path in url]
    return urls


def crawl(
    root_url: str,
    use_sitemap: bool = False,
    sitemap_url: str | None = None,
    filter_path: str | None = None,
) -> None:
    """Crawl pages starting from a root URL.

    If ``use_sitemap`` is true, URLs are pulled from the sitemap instead of the
    root page. The logic mirrors the legacy implementation in
    ``src/services/crawler.py`` so that both interfaces stay in sync.
    """

    if use_sitemap:
        if not sitemap_url:
            raise ValueError("Sitemap URL must be provided if use_sitemap=True")
        links = discover_links_from_sitemap(sitemap_url, filter_path)
    else:
        links = discover_links_from_page(root_url)

    print(f"Discovered {len(links)} links")

    storage_root = resolve_blob_root(BLOB_ROOT)

    for link in links:
        path = article_path(link)

        if has_been_extracted(link, blob_root=storage_root):
            continue  # skip if already stored

        try:
            response = requests.get(link, headers=HEADERS, timeout=(10, 60))
            response.raise_for_status()
            title, text = extract_text(response.text)

            if not text or len(text) < 200:
                print(f"Too little text, skip: {link}")
                continue

            payload = {
                "url": link,
                "title": title,
                "fetched_at": datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "text": text,
            }
            store_json(path, payload, blob_root=storage_root)
            record_stored_url(link, blob_root=storage_root)
            print(f"Stored {link}")
        except Exception as exc:  # noqa: BLE001 - broad catch keeps crawl running
            print(f"Failed {link}: {exc}")


class Article(BaseModel):
    """Representation of a discovered article."""

    url: HttpUrl
    title: str = Field(default="")
    summary: str | None = Field(default=None)
    topics: List[str] = Field(default_factory=list)


class SiteCrawlResult(BaseModel):
    """Container returned from :class:`SiteCrawler.fetch`."""

    site: SiteConfig
    articles: List[Article] = Field(default_factory=list)


class SiteCrawler:
    """Simple HTML crawler that extracts internal article links."""

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    # Maintain parity with helper functions from ``src/services/crawler.py``.
    store_json = staticmethod(store_json)
    record_stored_url = staticmethod(record_stored_url)
    has_been_extracted = staticmethod(has_been_extracted)
    article_path = staticmethod(article_path)
    extract_text = staticmethod(extract_text)
    discover_links_from_page = staticmethod(discover_links_from_page)
    discover_links_from_sitemap = staticmethod(discover_links_from_sitemap)
    crawl = staticmethod(crawl)

    def fetch(self, site: SiteConfig) -> SiteCrawlResult:
        """Fetch a site and return candidate article links."""

        response = self._session.get(str(site.url), timeout=(10, 60))
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        articles = list(self._extract_articles(soup, site.topics, str(site.url)))
        return SiteCrawlResult(site=site, articles=articles)

    def _extract_articles(
        self, soup: BeautifulSoup, topics: Sequence[str], base_url: str
    ) -> Iterator[Article]:
        """Yield :class:`Article` objects discovered within ``soup``."""

        parsed_base = urlparse(base_url)
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            if not href:
                continue

            candidate = urljoin(base_url, href)
            parsed_candidate = urlparse(candidate)

            if parsed_candidate.scheme not in {"http", "https"}:
                continue
            if parsed_candidate.netloc and parsed_candidate.netloc != parsed_base.netloc:
                continue

            normalized = candidate.split("#", 1)[0]
            if normalized in seen:
                continue
            seen.add(normalized)

            title = anchor.get_text(" ", strip=True)
            if topics:
                lowered = title.lower()
                if not any(topic.lower() in lowered for topic in topics):
                    continue

            summary = self._build_summary(title=title, url=normalized)
            yield Article(url=normalized, title=title, summary=summary, topics=list(topics))

    def _build_summary(self, *, title: str, url: str) -> str:
        """Return a lightweight summary for an article link."""

        return title or url
