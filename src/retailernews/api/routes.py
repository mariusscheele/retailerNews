"""API routes for the Retailer News backend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from retailernews.config import AppConfig, SiteConfig
from retailernews.services.crawler import SiteCrawler

router = APIRouter()


def get_config() -> AppConfig:
    return AppConfig.from_file()


def get_crawler() -> SiteCrawler:
    return SiteCrawler()


@router.get("/sites", response_model=list[SiteConfig])
def list_sites(config: AppConfig = Depends(get_config)) -> list[SiteConfig]:
    return config.sites


@router.post("/sites", response_model=SiteConfig, status_code=201)
def add_site(site: SiteConfig, config: AppConfig = Depends(get_config)) -> SiteConfig:
    config.add_site(site)
    config.dump()
    return site


@router.delete("/sites/{url}", status_code=204)
def delete_site(url: str, config: AppConfig = Depends(get_config)) -> None:
    existing = [site for site in config.sites if site.url == url]
    if not existing:
        raise HTTPException(status_code=404, detail="Site not found")
    config.remove_site(url)
    config.dump()


@router.post("/crawl", response_model=list)
def crawl_all(
    config: AppConfig = Depends(get_config), crawler: SiteCrawler = Depends(get_crawler)
) -> list:
    results = []
    for site in config.sites:
        result = crawler.fetch(site)
        results.append(result.model_dump())
    return results
