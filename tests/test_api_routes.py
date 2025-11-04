"""Tests for helper utilities in :mod:`retailernews.api.routes`."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from retailernews.api.app import create_app
from retailernews.api.routes import (
    CategorySummary,
    SummariesResponse,
    load_latest_digest,
    store_latest_digest,
)
from retailernews.services.summarizer import default_category_advice_prompt


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


def test_retrieve_category_advice_returns_advice() -> None:
    """The advice endpoint should return guidance when a summary exists."""

    stored = SummariesResponse(
        digest="",
        blob_root="/tmp/blob",
        model="demo",
        categories=[
            CategorySummary(
                name="Customer Experience",
                slug="customer-experience",
                summary="The summary",
            )
        ],
    )

    app = create_app()
    client = TestClient(app)

    with patch("retailernews.api.routes.load_latest_digest", return_value=stored), patch(
        "retailernews.api.routes.generate_category_advice",
        return_value="Actionable advice",
    ) as mock_generate:
        response = client.get("/api/summaries/customer-experience/advice")

    assert response.status_code == 200
    payload = response.json()
    assert payload["advice"] == "Actionable advice"
    assert payload["category"]["slug"] == "customer-experience"
    assert payload["prompt"] == default_category_advice_prompt()
    mock_generate.assert_called_once_with("The summary", default_category_advice_prompt(), model="gpt-4o-mini")


def test_retrieve_category_advice_returns_404_when_missing_summary() -> None:
    """A helpful error is returned when no stored summary exists."""

    app = create_app()
    client = TestClient(app)

    with patch("retailernews.api.routes.load_latest_digest", return_value=None):
        response = client.get("/api/summaries/customer-experience/advice")

    assert response.status_code == 404
    assert response.json()["detail"]


def test_retrieve_category_advice_returns_404_for_unknown_category() -> None:
    """The endpoint should surface a 404 when the category isn't present."""

    stored = SummariesResponse(
        digest="",
        blob_root="/tmp/blob",
        model="demo",
        categories=[
            CategorySummary(name="Store Operations", slug="store-operations", summary=""),
        ],
    )

    app = create_app()
    client = TestClient(app)

    with patch("retailernews.api.routes.load_latest_digest", return_value=stored):
        response = client.get("/api/summaries/customer-experience/advice")

    assert response.status_code == 404
    assert "Customer Experience" in response.json()["detail"]


def test_customer_loyalty_page_is_served() -> None:
    """The dedicated customer loyalty workspace should be accessible."""

    app = create_app()
    client = TestClient(app)

    response = client.get("/customer-loyalty")

    assert response.status_code == 200
    body = response.text
    assert "hub for kundelojalitet" in body
    assert "/api/summaries/customer-loyalty/advice" in body
