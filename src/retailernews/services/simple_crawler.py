"""Simple filesystem-backed crawler for downloading article pages."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BLOBSTORE_ROOT = Path("./blobstore")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)


def store_json(path: Path | str, payload: dict) -> None:
    """Persist *payload* to *path* in UTF-8 encoded JSON."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


def _discover_links(soup: BeautifulSoup, root_url: str) -> Set[str]:
    """Return all absolute links that share the *root_url* prefix."""

    discovered: Set[str] = set()
    prefix = root_url.rstrip("/")
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if not href:
            continue
        absolute = urljoin(root_url, href)
        if absolute.startswith(prefix):
            discovered.add(absolute)
    return discovered


def _article_exists(root_url: str, article_url: str) -> bool:
    """Check whether *article_url* has already been stored in the blobstore."""

    netloc = urlparse(root_url).netloc or urlparse(article_url).netloc
    fingerprint = hashlib.sha1(article_url.encode("utf-8")).hexdigest()
    site_root = BLOBSTORE_ROOT / f"site={netloc}"
    search_pattern = f"**/{fingerprint}.json"
    return any(site_root.glob(search_pattern))


def _build_blob_path(root_url: str, article_url: str, fetched_at: datetime) -> Path:
    netloc = urlparse(root_url).netloc or urlparse(article_url).netloc
    date_folder = fetched_at.strftime("%Y%m%d")
    fingerprint = hashlib.sha1(article_url.encode("utf-8")).hexdigest()
    return BLOBSTORE_ROOT / f"site={netloc}" / date_folder / f"{fingerprint}.json"


def _clean_text(soup: BeautifulSoup) -> str:
    for element in soup(["script", "style"]):
        element.decompose()

    article = soup.find("article") or soup.body or soup
    text = article.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _fetch_article(url: str) -> tuple[str, str]:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else url
    text = _clean_text(soup)
    return title, text


def crawl(root_url: str) -> None:
    """Fetch *root_url* and persist all article pages under the same prefix."""

    response = requests.get(root_url, headers={"User-Agent": USER_AGENT}, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    article_urls = _discover_links(soup, root_url)

    logger.info("Discovered %d candidate articles from %s", len(article_urls), root_url)

    for article_url in article_urls:
        if _article_exists(root_url, article_url):
            logger.debug("Skipping %s because it already exists in blobstore", article_url)
            continue

        try:
            title, text = _fetch_article(article_url)
        except requests.RequestException as exc:
            logger.warning("Failed to fetch %s: %s", article_url, exc)
            continue

        fetched_at = datetime.utcnow()
        blob_path = _build_blob_path(root_url, article_url, fetched_at)
        payload = {
            "url": article_url,
            "title": title,
            "fetched_at": fetched_at.replace(microsecond=0).isoformat() + "Z",
            "text": text,
        }
        store_json(blob_path, payload)
        logger.info("Stored article %s", blob_path)


__all__ = ["crawl", "store_json"]
