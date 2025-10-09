from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from retailernews.config import (
    AppConfig,
    CategoriesConfig,
    CategoryConfig,
    SiteConfig,
    TopicConfig,
)
from retailernews.services.summarizer import classify_summary


def test_round_trip(tmp_path: Path) -> None:
    config_path = tmp_path / "sites.json"
    config = AppConfig(sites=[SiteConfig(name="Test", url="https://example.com", topics=["retail"])])
    config.dump(config_path)

    loaded = AppConfig.from_file(config_path)
    assert loaded.sites[0].name == "Test"
    assert loaded.sites[0].topics == ["retail"]


def test_categories_round_trip(tmp_path: Path) -> None:
    config_path = tmp_path / "categories.json"
    config = CategoriesConfig(
        categories=[
            CategoryConfig(
                name="Operations",
                topics=[TopicConfig(name="Logistics", keywords=["supply chain"])],
            )
        ]
    )
    config.dump(config_path)

    loaded = CategoriesConfig.from_file(config_path)
    assert loaded.categories[0].name == "Operations"
    assert loaded.categories[0].topics[0].keyword_set() == {"Logistics", "supply chain"}


def test_classify_summary_matches_keywords() -> None:
    config = CategoriesConfig(
        categories=[
            CategoryConfig(
                name="Digital",
                topics=[TopicConfig(name="E-commerce", keywords=["online sales"])],
            ),
            CategoryConfig(name="Stores", topics=[TopicConfig(name="Operations")]),
        ]
    )

    categories, topics = classify_summary(
        "Retailer reports booming online sales in Q4", "Stores improved operations", config
    )

    assert categories == ["Digital", "Stores"]
    assert topics == ["E-commerce", "Operations"]
