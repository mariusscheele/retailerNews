"""Configuration models and helpers for the Retailer News crawler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, ValidationError

__all__ = [
    "AppConfig",
    "SiteConfig",
    "DEFAULT_CONFIG_PATH",
    "TopicConfig",
    "CategoryConfig",
    "CategoriesConfig",
    "DEFAULT_CATEGORIES_PATH",
]

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "sites.json"
DEFAULT_CATEGORIES_PATH = Path(__file__).resolve().parents[2] / "data" / "categories.json"


class SiteConfig(BaseModel):
    """Configuration for a single site to crawl."""

    name: str = Field(..., description="Human friendly site name")
    url: HttpUrl = Field(..., description="Base URL to crawl")
    root: HttpUrl | None = Field(
        default=None,
        description=(
            "Base URL that discovered article links must match. "
            "Defaults to the crawl URL when omitted."
        ),
    )
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
    use_playwright: bool = Field(
        default=False,
        description=(
            "Whether to fetch pages using Playwright instead of plain HTTP requests. "
            "This can help when sites rely on heavy client-side rendering or strict "
            "bot protection."
        ),
    )

    @property
    def article_root(self) -> str:
        """Return the canonical root URL expected for discovered articles."""

        root = self.root if self.root is not None else self.url
        return str(root)

    def allows_url(self, candidate_url: str) -> bool:
        """Return ``True`` when ``candidate_url`` matches the configured root."""

        expected = urlparse(self.article_root)
        candidate = urlparse(candidate_url)

        if expected.netloc and candidate.netloc != expected.netloc:
            return False

        expected_path = expected.path.rstrip("/")
        if expected_path and not candidate.path.startswith(expected_path):
            return False

        return True


class TopicConfig(BaseModel):
    """Configuration for a topic that may be tagged against summaries."""

    name: str = Field(..., description="Human friendly topic name")
    keywords: List[str] = Field(
        default_factory=list,
        description=(
            "Optional list of keywords that should map an article or summary to this topic. "
            "When omitted the topic name is used as the keyword."
        ),
    )

    def keyword_set(self) -> set[str]:
        """Return the set of keywords (including the topic name)."""

        values = {self.name}
        values.update(self.keywords)
        return {keyword for keyword in values if keyword}


class CategoryConfig(BaseModel):
    """A high level category and its associated topics."""

    name: str = Field(..., description="Category label")
    topics: List[TopicConfig] = Field(default_factory=list)


class CategoriesConfig(BaseModel):
    """Collection of categories/topics that can be applied to summaries."""

    categories: List[CategoryConfig] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path | str | None = None) -> "CategoriesConfig":
        """Load category configuration from disk, returning an empty config if missing."""

        config_path = Path(path) if path else DEFAULT_CATEGORIES_PATH
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in configuration file: {config_path}") from exc

        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Configuration file is invalid: {config_path}\n{exc}") from exc

    def dump(self, path: Path | str | None = None) -> None:
        """Persist category configuration back to disk as JSON."""

        config_path = Path(path) if path else DEFAULT_CATEGORIES_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(self.model_dump_json(indent=2), encoding="utf-8")


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
