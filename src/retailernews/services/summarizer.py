"""Summarisation helpers exposed through the API."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from retailernews.blobstore import DEFAULT_BLOB_ROOT, resolve_blob_root
from retailernews.config import CategoriesConfig

try:  # pragma: no cover - optional dependency during tests
    from openai import OpenAI
except ModuleNotFoundError:  # pragma: no cover - optional dependency during tests
    OpenAI = None  # type: ignore[assignment]
    _client = None
else:
    _client = None

    def _load_openai_api_key() -> str | None:
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            return env_key

        env_path = None
        current = Path(__file__).resolve().parent
        for candidate in (current, *current.parents):
            possible = candidate / ".env"
            if possible.exists():
                env_path = possible
                break

        if env_path is None:
            return None

        try:
            with env_path.open("r", encoding="utf-8") as env_file:
                for raw_line in env_file:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key.strip() == "OPENAI_API_KEY":
                        return value.strip().strip('"').strip("'")
        except OSError:
            return None

        return None

    def _initialise_client() -> "OpenAI":
        api_key = _load_openai_api_key()
        if api_key:
            return OpenAI(api_key=api_key)
        # Let the OpenAI client pick up configuration from its defaults, but provide a clearer
        # error message if that still fails.
        return OpenAI()


def _get_client() -> "OpenAI":
    if OpenAI is None:  # pragma: no cover - runtime guard
        raise RuntimeError(
            "OpenAI client is not available. Install the 'openai' package and set OPENAI_API_KEY "
            "(either in the environment or in a .env file)."
        )

    global _client
    if _client is None:
        try:
            _client = _initialise_client()
        except Exception as exc:  # pragma: no cover - defensive guard
            raise RuntimeError(
                "Failed to initialise the OpenAI client. Ensure OPENAI_API_KEY is configured either in the "
                "environment or in a .env file."
            ) from exc

    return _client


def summarize_single_article(text: str, title: str = "", model: str = "gpt-4o-mini") -> str:
    """Summarize a single article into concise bullet points."""

    truncated_text = text[:4000] if text else ""

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "You are an assistant that summarizes retail industry news into concise bullet points.",
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Summarize the following article into 3-5 short bullet points focusing on key facts and "
                        "implications for retail executives.\n\nTitle: {title}\n\nContent:\n{content}".format(
                            title=title or "(untitled)",
                            content=truncated_text,
                        )
                    ),
                }
            ],
        },
    ]

    print(f"Summarizing article: {title or 'Untitled'}")
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()


def store_summary(
    blob_root: str | Path,
    url: str,
    title: str,
    summary: str,
    *,
    categories: list[str] | None = None,
    topics: list[str] | None = None,
) -> None:
    """Persist the summary JSON into the summaries blobstore."""

    root = resolve_blob_root(blob_root)
    parsed = urlparse(url)
    host = parsed.netloc or "unknown"
    date_folder = datetime.utcnow().strftime("%Y%m%d")
    sha = hashlib.sha1(url.encode("utf-8")).hexdigest()

    summary_dir = root / "summaries" / f"site={host}" / date_folder
    summary_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "url": url,
        "title": title,
        "summary": summary,
        "summarized_at": datetime.utcnow().isoformat(),
    }

    if categories:
        payload["categories"] = categories
    if topics:
        payload["topics"] = topics

    output_path = summary_dir / f"{sha}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Stored summary for {title or url} at {output_path}")



@dataclass(slots=True)
class ArticleSummary:
    """Summary metadata captured for each processed article."""

    title: str
    url: str
    summary: str
    categories: list[str]
    topics: list[str]


@dataclass(slots=True)
class CategoryDigest:
    """Digest of summaries associated with a specific category."""

    name: str
    slug: str
    summary: str


@dataclass(slots=True)
class MapReduceResult:
    """Container for the outputs of the map-reduce summarisation pipeline."""

    digest: str
    categories: list[CategoryDigest]


def _load_categories_config() -> CategoriesConfig:
    """Attempt to load the category configuration file."""

    try:
        return CategoriesConfig.from_file()
    except FileNotFoundError:
        return CategoriesConfig()
    except ValueError as exc:
        print(f"Category configuration could not be loaded: {exc}")
        return CategoriesConfig()


def classify_summary(
    summary: str, article_text: str, config: CategoriesConfig
) -> tuple[list[str], list[str]]:
    """Return matching categories and topics based on configured keywords."""

    if not config.categories:
        return ([], [])

    haystacks = [summary.lower(), article_text.lower()]
    matched_categories: set[str] = set()
    matched_topics: set[str] = set()

    for category in config.categories:
        for topic in category.topics:
            keywords = {keyword.lower() for keyword in topic.keyword_set()}
            keywords.discard("")
            if not keywords:
                continue

            if any(keyword in haystack for keyword in keywords for haystack in haystacks):
                matched_categories.add(category.name)
                matched_topics.add(topic.name)
                break

    return (sorted(matched_categories), sorted(matched_topics))


_SLUGIFY_RE = re.compile(r"[^a-z0-9]+")


def _slugify_category_name(name: str) -> str:
    """Generate a URL-friendly slug for the provided category name."""

    slug = _SLUGIFY_RE.sub("-", name.lower()).strip("-")
    return slug or "category"


def _summarize_category_articles(
    entries: List[ArticleSummary], model: str = "gpt-4o-mini"
) -> str:
    """Generate a cohesive summary for a collection of category articles."""

    if not entries:
        return "No updates available for this category yet."

    combined_sections: list[str] = []
    for entry in entries:
        header = entry.title or entry.url or "(untitled article)"
        source_line = f"Source: {entry.url}" if entry.url else "Source: Unknown"
        combined_sections.append(
            f"{header}\n{source_line}\nSummary:\n{entry.summary}".strip()
        )

    combined_text = "\n\n".join(combined_sections)
    truncated_text = combined_text[:6000]

    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that synthesises retail news into concise digests for executives. "
                "Write a single cohesive summary that blends the key developments, risks, and opportunities "
                "across the provided updates. Always reference supporting URLs inline using the format "
                "(Source: https://example.com)."
            ),
        },
        {
            "role": "user",
            "content": (
                "Create a category summary that highlights what retail leaders should know. Keep it focused "
                "and action-oriented while citing the relevant source URL immediately after each fact.\n\n"
                f"Article updates:\n{truncated_text}"
            ),
        },
    ]

    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()


def _build_category_digests(
    summaries: List[ArticleSummary], config: CategoriesConfig, *, model: str = "gpt-4o-mini"
) -> list[CategoryDigest]:
    """Produce concatenated digests for each configured category."""

    digests: list[CategoryDigest] = []

    for category in config.categories:
        matched = [entry for entry in summaries if category.name in entry.categories]

        if matched:
            summary_text = _summarize_category_articles(matched, model=model)
        else:
            summary_text = "No updates available for this category yet."

        digests.append(
            CategoryDigest(
                name=category.name,
                slug=_slugify_category_name(category.name),
                summary=summary_text,
            )
        )

    return digests


def map_summarize_articles(
    blob_root: str | Path = DEFAULT_BLOB_ROOT, model: str = "gpt-4o-mini"
) -> List[ArticleSummary]:
    """Summarize all articles within the blobstore and store results."""

    summaries: List[ArticleSummary] = []
    root_path = resolve_blob_root(blob_root)

    if not root_path.exists():
        print(f"Blob root {blob_root} does not exist. Nothing to summarize.")
        return summaries

    categories_config = _load_categories_config()

    for article_path in root_path.rglob("*.json"):

        if "summaries" in article_path.parts:
            continue
        if "stored_urls" in article_path.name:
            continue
        try:
            with article_path.open("r", encoding="utf-8") as f:
                article = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Skipping {article_path}: {exc}")
            continue
        print(article_path)
        text = article.get("text", "")
        title = article.get("title", "")
        url = article.get("url", "")
        summary = summarize_single_article(text=text or "", title=title or "", model=model)
        categories, topics = classify_summary(summary, text or "", categories_config)
        summaries.append(
            ArticleSummary(
                title=title or "",
                url=url or "",
                summary=summary,
                categories=categories,
                topics=topics,
            )
        )
        store_summary(
            root_path,
            url=url or "",
            title=title or "",
            summary=summary,
            categories=categories,
            topics=topics,
        )

    return summaries


def reduce_summaries(summaries: List[ArticleSummary], model: str = "gpt-4o-mini") -> str:
    """Produce an overall digest from individual summaries."""

    if not summaries:
        return "No summaries available."

    combined_sections: List[str] = []
    for entry in summaries:
        header = entry.title or entry.url or "(untitled article)"
        source_line = f"Source: {entry.url}" if entry.url else "Source: Unknown"
        combined_sections.append(f"{header}\n{source_line}\n{entry.summary}")

    combined = "\n\n".join(combined_sections)
    messages = [
        {
            "role": "system",
            "content": (
                "You craft executive-ready digests highlighting major retail trends. "
                "Always cite supporting source URLs inline immediately after the relevant sentence "
                "using the format (Source: https://example.com). Do not place sources in a "
                "standalone list."
            ),
        },
        {
            "role": "user",
            "content": (
                "Using the following bullet-point summaries from recent retail news, produce a cohesive digest "
                "that highlights key themes, risks, and opportunities for retail executives. Keep it concise and "
                "action-oriented. Cite the exact source URL inline immediately after the supporting statement and "
                "avoid grouping sources at the end.\n\nSummaries:\n{summaries}".format(summaries=combined)
            ),
        },
    ]

    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def map_reduce_summarize(
    blob_root: str | Path = DEFAULT_BLOB_ROOT, model: str = "gpt-4o-mini"
) -> MapReduceResult:
    """Run the full map-reduce summarization pipeline."""

    summaries = map_summarize_articles(blob_root=blob_root, model=model)
    digest = reduce_summaries(summaries=summaries, model=model)
    categories_config = _load_categories_config()
    category_digests = _build_category_digests(summaries, categories_config, model=model)

    return MapReduceResult(digest=digest, categories=category_digests)


__all__ = [
    "map_reduce_summarize",
    "map_summarize_articles",
    "reduce_summaries",
    "store_summary",
    "summarize_single_article",
    "ArticleSummary",
    "classify_summary",
    "CategoryDigest",
    "MapReduceResult",
]
