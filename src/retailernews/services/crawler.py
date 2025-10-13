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
MAX_INTERNAL_LINKS = 10
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
    datestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return f"site={host}/{datestamp}/{url_hash}.json"


def find_published_date(html: str) -> str | None:
    """Attempt to extract a published date string from article HTML."""

    soup = BeautifulSoup(html, "lxml")

    meta_selectors = [
        {"property": "article:published_time"},
        {"name": "pubdate"},
        {"name": "publish-date"},
        {"name": "publication_date"},
        {"name": "date"},
        {"itemprop": "datePublished"},
    ]

    for attrs in meta_selectors:
        tag = soup.find("meta", attrs=attrs)
        if not tag:
            continue
        for attribute in ("content", "datetime", "value"):
            value = tag.get(attribute)
            if value:
                return value.strip()
        text = tag.get_text(strip=True)
        if text:
            return text

    for time_tag in soup.find_all("time"):
        for attribute in ("datetime", "content", "title"):
            value = time_tag.get(attribute)
            if value:
                return value.strip()
        text = time_tag.get_text(strip=True)
        if text:
            return text

    return None


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
    counter = 0
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        absolute_url = urljoin(root_url, href)
        parsed = urlparse(absolute_url)

        if parsed.netloc != root_netloc:
            continue
        if not parsed.path.startswith(root_path):
            continue

        found.add(absolute_url.split("#")[0])  # drop fragments
        counter += 1
        if counter > MAX_INTERNAL_LINKS:
            break
    return list(found)


def discover_links_from_sitemap(
    sitemap_url: str, filter_path: str | None = None
) -> List[str]:
    """Parse sitemap.xml and return links (optionally filtered by path)."""

    response = requests.get(sitemap_url, headers=HEADERS, timeout=(10, 120))
    
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

            datestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
            payload = {
                "url": link,
                "title": title,
                "fetched_at": datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "datestamp": datestamp,
                "text": text,
            }
            published_at = find_published_date(response.text)
            if published_at:
                payload["published_at"] = published_at
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
    text: str | None = Field(default=None, description="Full article text when extracted")


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
    find_published_date = staticmethod(find_published_date)
    discover_links_from_page = staticmethod(discover_links_from_page)
    discover_links_from_sitemap = staticmethod(discover_links_from_sitemap)
    crawl = staticmethod(crawl)

    def fetch(self, site: SiteConfig) -> SiteCrawlResult:
        """Fetch a site, extract article links and retrieve new article content."""

        base_url = str(site.url)

        if site.use_sitemap:
            if not site.sitemap_url:
                raise ValueError("Sitemap URL must be provided when use_sitemap is True")
            links = self.discover_links_from_sitemap(str(site.sitemap_url), site.filter_path)
            discovered_articles = [
                Article(url=link, topics=list(site.topics), summary=self._build_summary(title="", url=link))
                for link in links
                if site.allows_url(link)
            ]
        else:
            response = self._session.get(base_url, timeout=(10, 60))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            discovered_articles = list(self._extract_articles(soup, site.topics, base_url))

        storage_root = resolve_blob_root(BLOB_ROOT)
        enriched_articles: List[Article] = []

        discovered_articles = [
            article for article in discovered_articles if site.allows_url(str(article.url))
        ]

        for article in discovered_articles:
            url = str(article.url)

            if self.has_been_extracted(url, blob_root=storage_root):
                enriched_articles.append(article)
                continue

            try:
                article_response = self._session.get(url, timeout=(10, 60))
                article_response.raise_for_status()
                title, text = self.extract_text(article_response.text)
            except requests.RequestException as exc:
                print(f"Failed {url}: {exc}")
                continue

            if not text or len(text) < 200:
                print(f"Too little text, skip: {url}")
                continue

            article_data = article.model_dump()
            article_data["title"] = title or article_data.get("title", "")
            if not article_data.get("summary"):
                article_data["summary"] = self._build_summary(title=article_data["title"], url=url)
            article_data["text"] = text

            datestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")
            payload = {
                "url": url,
                "title": article_data["title"],
                "fetched_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "datestamp": datestamp,
                "text": text,
            }
            published_at = self.find_published_date(article_response.text)
            if published_at:
                payload["published_at"] = published_at

            path = self.article_path(url)
            self.store_json(path, payload, blob_root=storage_root)
            self.record_stored_url(url, blob_root=storage_root)

            enriched_articles.append(Article(**article_data))

        return SiteCrawlResult(site=site, articles=enriched_articles)

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
