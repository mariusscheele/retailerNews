"""Application configuration utilities."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List

from pydantic import BaseModel, Field

DEFAULT_SITES_PATH = Path(os.getenv("RETAILERNEWS_SITES_PATH", "data/sites.json"))


class SiteConfig(BaseModel):
    """Configuration for a single site to crawl."""

    name: str = Field(..., description="Human readable name of the source")
    url: str = Field(..., description="Root URL to crawl")
    topics: List[str] = Field(default_factory=list, description="Topics of interest")


class AppConfig(BaseModel):
    """Top level configuration."""

    sites: List[SiteConfig]

    @classmethod
    def from_file(cls, path: Path | str | None = None) -> "AppConfig":
        file_path = Path(path) if path is not None else DEFAULT_SITES_PATH
        if not file_path.exists():
            raise FileNotFoundError(f"Site configuration not found at {file_path}")

        with file_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        sites = data.get("sites", [])
        return cls(sites=[SiteConfig(**item) for item in sites])

    def dump(self, path: Path | str | None = None) -> None:
        file_path = Path(path) if path is not None else DEFAULT_SITES_PATH
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"sites": [site.model_dump() for site in self.sites]}
        with file_path.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2)

    def add_site(self, site: SiteConfig) -> None:
        self.sites.append(site)

    def remove_site(self, url: str) -> None:
        self.sites = [site for site in self.sites if site.url != url]

    def iter_topics(self) -> Iterable[str]:
        seen = set()
        for site in self.sites:
            for topic in site.topics:
                if topic not in seen:
                    seen.add(topic)
                    yield topic
