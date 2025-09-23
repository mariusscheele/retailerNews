"""Simple crawling utilities."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List

import requests
from bs4 import BeautifulSoup
from readability import Document

from retailernews.config import SiteConfig
from retailernews.models import Article, CrawlResult

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0.0.0 Safari/537.36"
)


class SiteCrawler:
    """Crawler capable of extracting article summaries from a site."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def fetch(self, site: SiteConfig) -> CrawlResult:
        """Fetch the landing page of a site and extract candidate articles."""

        response = requests.get(site.url, headers={"User-Agent": USER_AGENT}, timeout=self.timeout)
        response.raise_for_status()

        document = Document(response.text)
        summary_html = document.summary()
        soup = BeautifulSoup(summary_html, "lxml")

        articles = list(self._extract_articles(soup, site.topics))
        return CrawlResult(source=site.name, articles=articles, fetched_at=datetime.utcnow())

    def _extract_articles(self, soup: BeautifulSoup, topics: Iterable[str]) -> Iterable[Article]:
        for link in soup.find_all("a"):
            title = link.get_text(strip=True)
            href = link.get("href")
            if not title or not href:
                continue

            lower_title = title.lower()
            matched_topics: List[str] = [topic for topic in topics if topic.lower() in lower_title]
            summary = self._build_summary(link)

            if matched_topics or summary:
                try:
                    article = Article(title=title, url=href, summary=summary, topics=matched_topics)
                    yield article
                except Exception as exc:  # pydantic validation error
                    logger.debug("Skipping article due to validation error: %s", exc)

    def _build_summary(self, link: BeautifulSoup) -> str | None:
        paragraph = link.find_parent("p")
        if paragraph:
            text = paragraph.get_text(strip=True)
            if text and len(text) > 40:
                return text
        return None
