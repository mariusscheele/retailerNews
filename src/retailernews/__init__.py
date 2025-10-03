"""Retailer News package exposing configuration, API, and service helpers."""

from __future__ import annotations

import os
from pathlib import Path


def _load_local_env() -> None:
    """Populate ``os.environ`` with variables from a project-level ``.env`` file."""

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        os.environ[key] = value.strip()


_load_local_env()

from .config import AppConfig, SiteConfig  # noqa: E402,F401

__all__ = ["AppConfig", "SiteConfig"]
