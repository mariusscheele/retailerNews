"""Simple crawling utilities."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from readability import Document
from dateutil import parser as date_parser

from retailernews.config import SiteConfig
from retailernews.models import Article, CrawlResult

logger = logging.getLogger(__name__)

BLOBSTORE_ROOT = Path("./blobstore")

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

        soup = BeautifulSoup(response.text, "lxml")
        fetched_at = datetime.now(timezone.utc)

        articles = list(self._extract_articles(soup, site.topics, site.url, fetched_at))
        return CrawlResult(source=site.name, articles=articles, fetched_at=fetched_at)

    def _extract_articles(
        self,
        soup: BeautifulSoup,
        topics: Iterable[str],
        site_url: str,
        fetched_at: datetime | None = None,
    ) -> Iterable[Article]:
        if fetched_at is None:
            fetched_at = datetime.now(timezone.utc)

        candidates: List[Tuple[str, str, List[str], BeautifulSoup]] = []
        seen_urls: set[str] = set()

        for link in soup.find_all("a"):
            title = link.get_text(strip=True)
            href = link.get("href")
            if not title or not href:
                continue

            article_url = urljoin(site_url, href)
            if not self._is_same_site(site_url, article_url):
                continue

            if article_url in seen_urls:
                continue

            seen_urls.add(article_url)

            lower_title = title.lower()
            matched_topics: List[str] = [topic for topic in topics if topic.lower() in lower_title]
            candidates.append((title, article_url, matched_topics, link))

        for title, article_url, matched_topics, link in candidates:
            summary_result = self._build_summary(link, article_url)
            if isinstance(summary_result, tuple):
                summary, text, published_at = summary_result
            else:
                summary = summary_result
                text = None
                published_at = None

            if matched_topics or summary or text:
                try:
                    article = Article(
                        title=title,
                        url=article_url,
                        summary=summary,
                        text=text,
                        published_at=published_at,
                        topics=matched_topics,
                    )
                except Exception as exc:  # pydantic validation error
                    logger.debug("Skipping article due to validation error: %s", exc)
                    continue

                self._store_article_blob(site_url, article, fetched_at)
                yield article

    def _build_summary(
        self, link: BeautifulSoup, article_url: str
    ) -> Tuple[str | None, str | None, datetime | None]:
        return self._build_article_details(link, article_url)

    def _build_article_details(
        self, link: BeautifulSoup, article_url: str
    ) -> Tuple[str | None, str | None, datetime | None]:
        paragraph = link.find_parent("p")
        summary: str | None = None
        if paragraph:
            text = paragraph.get_text(strip=True)
            if text and len(text) > 40:
                summary = text

        try:
            response = requests.get(article_url, headers={"User-Agent": USER_AGENT}, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.debug("Failed to fetch article for summary %s: %s", article_url, exc)
            return summary, None, None

        soup = BeautifulSoup(response.text, "lxml")
        published_at = self._extract_published_at(soup)
        article_text: str | None = None

        try:
            document = Document(response.text)
            summary_html = document.summary()
            summary_soup = BeautifulSoup(summary_html, "lxml")
            extracted_text = summary_soup.get_text(separator="\n", strip=True)
            if extracted_text:
                article_text = extracted_text
                if summary is None:
                    lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
                    summary = " ".join(lines) or None
        except Exception as exc:  # pragma: no cover - best effort parsing
            logger.debug("Failed to parse article body %s: %s", article_url, exc)

        if summary is None:
            text = soup.get_text(separator=" ", strip=True)
            summary = text or None

        return summary, article_text, published_at

    def _store_article_blob(self, site_url: str, article: Article, fetched_at: datetime) -> None:
        fingerprint = hashlib.sha1(str(article.url).encode("utf-8")).hexdigest()
        netloc = urlparse(site_url).netloc or urlparse(str(article.url)).netloc
        date_folder = fetched_at.strftime("%Y%m%d")
        blob_path = BLOBSTORE_ROOT / f"site={netloc}" / date_folder / f"{fingerprint}.json"

        fetched_iso = (
            fetched_at.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

        payload = {
            "url": str(article.url),
            "title": article.title,
            "fetched_at": fetched_iso,
            "text": article.text or "",
        }

        blob_path.parent.mkdir(parents=True, exist_ok=True)
        with blob_path.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)

    def _extract_published_at(self, soup: BeautifulSoup) -> datetime | None:
        candidates: List[str] = []

        meta_selectors = [
            ("meta", {"property": "article:published_time"}),
            ("meta", {"property": "og:published_time"}),
            ("meta", {"property": "og:publish_date"}),
            ("meta", {"name": "pubdate"}),
            ("meta", {"name": "publishdate"}),
            ("meta", {"name": "publish_date"}),
            ("meta", {"name": "date"}),
            ("meta", {"name": "DC.date.issued"}),
            ("meta", {"itemprop": "datePublished"}),
        ]

        for tag_name, attrs in meta_selectors:
            tag = soup.find(tag_name, attrs=attrs)
            if not tag:
                continue

            value = tag.get("content") or tag.get("datetime")
            if value:
                candidates.append(value)

        for time_tag in soup.find_all("time"):
            if time_tag.has_attr("datetime"):
                candidates.append(time_tag["datetime"])
            text = time_tag.get_text(strip=True)
            if text:
                candidates.append(text)

        date_class_indicators = ["date", "time", "publish", "posted"]
        for class_name in date_class_indicators:
            for element in soup.find_all(
                class_=lambda value, needle=class_name: self._class_matches(value, needle)
            ):
                text = element.get_text(strip=True)
                if text:
                    candidates.append(text)

        for candidate in candidates:
            parsed = self._parse_datetime(candidate)
            if parsed is not None:
                return parsed

        return None

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        try:
            parsed = date_parser.parse(value)
        except (ValueError, TypeError, OverflowError):
            return None

        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc)

        return parsed

    @staticmethod
    def _class_matches(value: object, needle: str) -> bool:
        if value is None:
            return False

        if isinstance(value, str):
            values = [value]
        else:
            try:
                values = list(value)  # type: ignore[arg-type]
            except TypeError:
                values = [str(value)]

        needle_lower = needle.lower()
        for item in values:
            if not isinstance(item, str):
                continue
            if needle_lower in item.lower():
                return True

        return False

    @staticmethod
    def _is_same_site(site_url: str, article_url: str) -> bool:
        root = urlparse(site_url)
        article = urlparse(article_url)

        if not root.netloc:
            return False

        if not article.netloc:
            return True

        return article.netloc == root.netloc
