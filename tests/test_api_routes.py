"""Tests for helper utilities in :mod:`retailernews.api.routes`."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from retailernews.api.routes import (
    CategorySummary,
    SummariesResponse,
    load_latest_digest,
    store_latest_digest,
)


def test_load_latest_digest_returns_none_when_missing() -> None:
    """When no digest file exists the helper should return ``None``."""

    with TemporaryDirectory() as tmpdir:
        assert load_latest_digest(tmpdir) is None


def test_store_and_load_latest_digest_round_trip() -> None:
    """Digest data written to disk can be read back successfully."""

    with TemporaryDirectory() as tmpdir:
        blob_root = Path(tmpdir)
        response = SummariesResponse(
            digest="Test digest",
            blob_root=str(blob_root),
            model="demo-model",
            categories=[
                CategorySummary(name="Category", slug="category", summary="Details here"),
            ],
        )

        store_latest_digest(response, blob_root=blob_root)

        loaded = load_latest_digest(blob_root)
        assert loaded is not None
        assert loaded.model_dump() == response.model_dump()
