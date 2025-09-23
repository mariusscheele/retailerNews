from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from retailernews.config import AppConfig, SiteConfig


def test_round_trip(tmp_path: Path) -> None:
    config_path = tmp_path / "sites.json"
    config = AppConfig(sites=[SiteConfig(name="Test", url="https://example.com", topics=["retail"])])
    config.dump(config_path)

    loaded = AppConfig.from_file(config_path)
    assert loaded.sites[0].name == "Test"
    assert loaded.sites[0].topics == ["retail"]
