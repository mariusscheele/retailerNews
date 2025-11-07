"""API routes exposing crawler and summariser functionality."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Body, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, ValidationError

from retailernews.blobstore import DEFAULT_BLOB_ROOT, ensure_blob_root
from retailernews.config import AppConfig
from retailernews.services.crawler import SiteCrawlResult, SiteCrawler
from retailernews.services.summarizer import (
    default_category_advice_prompt,
    generate_category_advice,
    map_reduce_summarize,
)

logger = logging.getLogger(__name__)

router = APIRouter()

LATEST_DIGEST_FILENAME = "latest_digest.json"


class CrawlError(BaseModel):
    site: str
    url: str
    error: str


class CrawlResponse(BaseModel):
    sites: List[SiteCrawlResult] = Field(default_factory=list)
    errors: List[CrawlError] = Field(default_factory=list)
    stored_urls: List[str] = Field(default_factory=list)


class CategorySummary(BaseModel):
    name: str
    slug: str
    summary: str


class SummariesResponse(BaseModel):
    digest: str
    blob_root: str
    model: str
    categories: List[CategorySummary] = Field(default_factory=list)


class SummariesRequest(BaseModel):
    blob_root: str | None = None
    model: str | None = None
    category: str | None = None
    sources: List[str] | None = None


class CategoryAdviceRequest(BaseModel):
    prompt: str | None = None
    model: str | None = None


class CategoryAdviceResponse(BaseModel):
    category: CategorySummary
    prompt: str
    advice: str
    model: str


class StoredUrlsResponse(BaseModel):
    urls: List[str] = Field(default_factory=list)


class SiteEntry(BaseModel):
    name: str
    slug: str
    host: str


class SitesResponse(BaseModel):
    sites: List[SiteEntry] = Field(default_factory=list)


def _latest_digest_path(blob_root: str | Path | None = None) -> Path:
    """Return the path to the file containing the most recent digest."""

    root = ensure_blob_root(blob_root)
    return root / LATEST_DIGEST_FILENAME


def store_latest_digest(response: "SummariesResponse", *, blob_root: str | Path | None = None) -> None:
    """Persist the latest digest response to disk."""

    payload = response.model_dump()
    payload["stored_at"] = datetime.now(UTC).isoformat()

    output_path = _latest_digest_path(blob_root)
    try:
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem failures are environmental
        logger.warning("Failed to store latest digest at %s: %s", output_path, exc)


def load_latest_digest(blob_root: str | Path | None = None) -> "SummariesResponse" | None:
    """Load the most recently stored digest if it exists."""

    path = _latest_digest_path(blob_root)
    if not path.exists():
        return None

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load latest digest from %s: %s", path, exc)
        return None

    raw_data.pop("stored_at", None)

    try:
        return SummariesResponse(**raw_data)
    except ValidationError as exc:
        logger.warning("Stored latest digest is invalid: %s", exc)
        return None


def _slugify_source(name: str) -> str:
    """Return a slug suitable for use in DOM element IDs."""

    normalized = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    slug = normalized.strip("-")
    return slug or "source"


@router.post("/crawl", response_model=CrawlResponse)
async def trigger_crawler() -> CrawlResponse:
    """Run the crawler for every configured site and return the results."""

    try:
        config = AppConfig.from_file()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    crawler = SiteCrawler()
    successes: List[SiteCrawlResult] = []
    errors: List[CrawlError] = []

    for site in config.sites:
        try:
            result: SiteCrawlResult = await run_in_threadpool(
                crawler.fetch,
                site,
                use_sitemap=site.use_sitemap,
                sitemap_url=str(site.sitemap_url) if site.sitemap_url is not None else None,
                filter_path=site.filter_path,
            )
        except requests.RequestException as exc:
            logger.exception("Failed to crawl %s", site.url)
            errors.append(CrawlError(site=site.name, url=str(site.url), error=str(exc)))
            continue
        successes.append(result)

    stored_urls = SiteCrawler.load_recorded_urls(blob_root=DEFAULT_BLOB_ROOT)

    return CrawlResponse(sites=successes, errors=errors, stored_urls=stored_urls)


@router.get("/crawl/urls", response_model=StoredUrlsResponse)
async def list_crawled_urls() -> StoredUrlsResponse:
    """Return a list of URLs that have previously been stored by the crawler."""

    urls = SiteCrawler.load_recorded_urls(blob_root=DEFAULT_BLOB_ROOT)
    return StoredUrlsResponse(urls=urls)


@router.get("/sites", response_model=SitesResponse)
async def list_sites() -> SitesResponse:
    """Return the configured set of crawlable sites."""

    try:
        config = AppConfig.from_file()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    entries: List[SiteEntry] = []
    for site in config.sites:
        parsed = urlparse(site.article_root)
        host = parsed.netloc or urlparse(str(site.url)).netloc
        entries.append(SiteEntry(name=site.name, slug=_slugify_source(site.name), host=host))

    return SitesResponse(sites=entries)


@router.post("/summaries", response_model=SummariesResponse)
async def trigger_summarizer(
    payload: SummariesRequest | None = Body(default=None),
) -> SummariesResponse:
    """Execute the map-reduce summariser pipeline."""

    request_payload = payload or SummariesRequest()

    blob_root = request_payload.blob_root or str(DEFAULT_BLOB_ROOT)
    model = request_payload.model or "gpt-4o-mini"
    category = request_payload.category

    included_sources: set[str] | None = None
    if request_payload.sources is not None:
        normalized = {
            source.strip().lower()
            for source in request_payload.sources
            if isinstance(source, str) and source.strip()
        }
        if not normalized:
            raise HTTPException(status_code=400, detail="Velg minst én nyhetskilde.")
        included_sources = normalized

    try:
        result = await run_in_threadpool(
            map_reduce_summarize,
            blob_root,
            model,
            included_sources,
        )
    except Exception as exc:  # pragma: no cover - defensive guard for external service errors
        logger.exception("Summarisation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    selected_categories = result.categories
    if category:
        selected_categories = [entry for entry in result.categories if entry.slug == category]
        if not selected_categories:
            raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    response = SummariesResponse(
        digest=result.digest,
        blob_root=blob_root,
        model=model,
        categories=[
            CategorySummary(name=entry.name, slug=entry.slug, summary=entry.summary)
            for entry in selected_categories
        ],
    )

    store_latest_digest(response)

    return response


@router.get("/summaries/latest", response_model=SummariesResponse)
async def retrieve_latest_summary() -> SummariesResponse:
    """Return the most recently generated digest if one exists."""

    stored = load_latest_digest()
    if stored is not None:
        return stored

    return SummariesResponse(digest="", blob_root=str(DEFAULT_BLOB_ROOT), model="", categories=[])


async def _build_category_advice(
    category_slug: str,
    *,
    prompt: str | None = None,
    model: str = "gpt-4o-mini",
) -> CategoryAdviceResponse:
    stored = load_latest_digest()
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="No stored summaries are available. Generate a summary to view strategic guidance.",
        )

    normalised_slug = category_slug.strip().lower()

    def _matches(entry: CategorySummary) -> bool:
        if entry.slug and entry.slug.lower() == normalised_slug:
            return True
        return bool(entry.name and entry.name.lower().replace(" ", "-") == normalised_slug)

    target = next((entry for entry in stored.categories if _matches(entry)), None)

    if target is None:
        display_name = category_slug.strip()
        if display_name:
            display_name = display_name.replace("-", " ").strip().title()
        else:
            display_name = "the requested category"
        raise HTTPException(
            status_code=404,
            detail=f"No category named '{display_name}' was found in the latest summary.",
        )

    final_prompt = (prompt or "").strip() or default_category_advice_prompt()

    try:
        advice = await run_in_threadpool(
            generate_category_advice,
            target.summary,
            final_prompt,
            model=model,
        )
    except Exception as exc:  # pragma: no cover - defensive guard for external service errors
        logger.exception("Failed to generate category advice for %s", category_slug)
        raise HTTPException(status_code=500, detail="Failed to generate strategic guidance.") from exc

    return CategoryAdviceResponse(category=target, prompt=final_prompt, advice=advice, model=model)


@router.get("/summaries/{category_slug}/advice", response_model=CategoryAdviceResponse)
async def retrieve_category_advice(category_slug: str, model: str = "gpt-4o-mini") -> CategoryAdviceResponse:
    """Return strategic guidance for the requested category using the latest summary."""

    return await _build_category_advice(category_slug, model=model)


@router.post("/summaries/{category_slug}/advice", response_model=CategoryAdviceResponse)
async def generate_category_advice_for_prompt(
    category_slug: str, payload: CategoryAdviceRequest
) -> CategoryAdviceResponse:
    """Generate strategic guidance for a category using a supplied prompt."""

    model = payload.model or "gpt-4o-mini"
    prompt = payload.prompt or ""

    return await _build_category_advice(category_slug, prompt=prompt, model=model)
