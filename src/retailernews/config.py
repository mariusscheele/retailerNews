"""Configuration models and helpers for the Retailer News crawler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from pydantic import BaseModel, Field, HttpUrl, ValidationError

__all__ = ["AppConfig", "SiteConfig", "DEFAULT_CONFIG_PATH"]

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "sites.json"


class SiteConfig(BaseModel):
    """Configuration for a single site to crawl."""

    name: str = Field(..., description="Human friendly site name")
    url: HttpUrl = Field(..., description="Base URL to crawl")
    topics: List[str] = Field(default_factory=list, description="Topics associated with the site")
    use_sitemap: bool = Field(
        default=False,
        description="Whether to fetch article URLs from an XML sitemap instead of the main page",
    )
    sitemap_url: HttpUrl | None = Field(
        default=None,
        description="Optional explicit sitemap URL to use when use_sitemap is true",
    )
    filter_path: str | None = Field(
        default=None,
        description="Optional path fragment used to filter sitemap entries",
    )


class AppConfig(BaseModel):
    """Collection of :class:`SiteConfig` entries for the crawler."""

    sites: List[SiteConfig] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path | str | None = None) -> "AppConfig":
        """Load configuration data from a JSON file."""

        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Configuration file not found: {config_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in configuration file: {config_path}") from exc

        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Configuration file is invalid: {config_path}\n{exc}") from exc

    def dump(self, path: Path | str | None = None) -> None:
        """Persist the configuration back to disk as JSON."""

        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def iter_sites(self) -> Iterable[SiteConfig]:
        """Iterate over configured sites."""

        return iter(self.sites)

    def add_site(self, site: SiteConfig) -> None:
        """Append a new site configuration to the collection."""

        self.sites.append(site)
