"""Summarisation helpers exposed through the API."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import urlparse

try:  # pragma: no cover - optional dependency during tests
    from openai import OpenAI
except ModuleNotFoundError:  # pragma: no cover - optional dependency during tests
    OpenAI = None  # type: ignore[assignment]
    _client = None
else:
    _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _get_client() -> "OpenAI":
    if _client is None:  # pragma: no cover - runtime guard
        raise RuntimeError(
            "OpenAI client is not available. Install the 'openai' package and set OPENAI_API_KEY."
        )
    return _client


def summarize_single_article(text: str, title: str = "", model: str = "gpt-4o-mini") -> str:
    """Summarize a single article into concise bullet points."""

    truncated_text = text[:4000] if text else ""
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that summarizes retail industry news into concise bullet points.",
        },
        {
            "role": "user",
            "content": (
                "Summarize the following article into 3-5 short bullet points focusing on key facts and implications "
                "for retail executives.\n\nTitle: {title}\n\nContent:\n{content}".format(
                    title=title or "(untitled)",
                    content=truncated_text,
                ),
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


def store_summary(blob_root: str, url: str, title: str, summary: str) -> None:
    """Persist the summary JSON into the summaries blobstore."""

    parsed = urlparse(url)
    host = parsed.netloc or "unknown"
    date_folder = datetime.utcnow().strftime("%Y%m%d")
    sha = hashlib.sha1(url.encode("utf-8")).hexdigest()

    summary_dir = Path(blob_root) / "summaries" / f"site={host}" / date_folder
    summary_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "url": url,
        "title": title,
        "summary": summary,
        "summarized_at": datetime.utcnow().isoformat(),
    }

    output_path = summary_dir / f"{sha}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def map_summarize_articles(blob_root: str = "./blobstore", model: str = "gpt-4o-mini") -> List[str]:
    """Summarize all articles within the blobstore and store results."""

    summaries: List[str] = []
    root_path = Path(blob_root)

    if not root_path.exists():
        return summaries

    for article_path in root_path.rglob("*.json"):
        if "summaries" in article_path.parts:
            continue
        try:
            with article_path.open("r", encoding="utf-8") as f:
                article = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        text = article.get("text", "")
        title = article.get("title", "")
        url = article.get("url", "")

        summary = summarize_single_article(text=text or "", title=title or "", model=model)
        summaries.append(summary)
        store_summary(blob_root, url=url or "", title=title or "", summary=summary)

    return summaries


def reduce_summaries(summaries: List[str], model: str = "gpt-4o-mini") -> str:
    """Produce an overall digest from individual summaries."""

    if not summaries:
        return "No summaries available."

    combined = "\n\n".join(summaries)
    messages = [
        {
            "role": "system",
            "content": "You craft executive-ready digests highlighting major retail trends.",
        },
        {
            "role": "user",
            "content": (
                "Using the following bullet-point summaries from recent retail news, produce a cohesive digest "
                "that highlights key themes, risks, and opportunities for retail executives. Keep it concise and "
                "action-oriented.\n\nSummaries:\n{summaries}".format(summaries=combined)
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


def map_reduce_summarize(blob_root: str = "./blobstore", model: str = "gpt-4o-mini") -> str:
    """Run the full map-reduce summarization pipeline."""

    summaries = map_summarize_articles(blob_root=blob_root, model=model)
    digest = reduce_summaries(summaries=summaries, model=model)
    return digest


__all__ = [
    "map_reduce_summarize",
    "map_summarize_articles",
    "reduce_summaries",
    "store_summary",
    "summarize_single_article",
]
