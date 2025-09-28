"""Domain models used across the application."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Article(BaseModel):
    """Representation of an extracted article."""

    title: str
    url: HttpUrl
    summary: Optional[str] = None
    text: Optional[str] = None
    published_at: Optional[datetime] = None
    topics: List[str] = Field(default_factory=list)


class CrawlResult(BaseModel):
    """Result of crawling a single site."""

    source: str
    articles: List[Article]
    fetched_at: datetime
