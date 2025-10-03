"""High level crawler implementation used by the API and CLI tools."""

from __future__ import annotations

from typing import Iterator, List, Sequence
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, HttpUrl

from retailernews.config import SiteConfig

__all__ = ["Article", "SiteCrawler", "SiteCrawlResult"]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    )
}


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
