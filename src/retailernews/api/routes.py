"""API routes exposing crawler and summariser functionality."""

from __future__ import annotations

import logging
from typing import List

import requests
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from retailernews.blobstore import DEFAULT_BLOB_ROOT
from retailernews.config import AppConfig
from retailernews.services.crawler import SiteCrawlResult, SiteCrawler
from retailernews.services.summarizer import map_reduce_summarize

logger = logging.getLogger(__name__)

router = APIRouter()


class CrawlError(BaseModel):
    site: str
    url: str
    error: str


class CrawlResponse(BaseModel):
    sites: List[SiteCrawlResult] = Field(default_factory=list)
    errors: List[CrawlError] = Field(default_factory=list)


class CategorySummary(BaseModel):
    name: str
    slug: str
    summary: str


class SummariesResponse(BaseModel):
    digest: str
    blob_root: str
    model: str
    categories: List[CategorySummary] = Field(default_factory=list)


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
            result: SiteCrawlResult = await run_in_threadpool(crawler.fetch, site)
        except requests.RequestException as exc:
            logger.exception("Failed to crawl %s", site.url)
            errors.append(CrawlError(site=site.name, url=str(site.url), error=str(exc)))
            continue
        successes.append(result)

    return CrawlResponse(sites=successes, errors=errors)


@router.post("/summaries", response_model=SummariesResponse)
async def trigger_summarizer(
    blob_root: str = str(DEFAULT_BLOB_ROOT),
    model: str = "gpt-4o-mini",
    category: str | None = None,
) -> SummariesResponse:
    """Execute the map-reduce summariser pipeline."""

    try:
        result = await run_in_threadpool(map_reduce_summarize, blob_root, model)
    except Exception as exc:  # pragma: no cover - defensive guard for external service errors
        logger.exception("Summarisation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    selected_categories = result.categories
    if category:
        selected_categories = [entry for entry in result.categories if entry.slug == category]
        if not selected_categories:
            raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    return SummariesResponse(
        digest=result.digest,
        blob_root=blob_root,
        model=model,
        categories=[
            CategorySummary(name=entry.name, slug=entry.slug, summary=entry.summary)
            for entry in selected_categories
        ],
    )
