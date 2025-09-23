"""ASGI entrypoint for running the Retailer News API with Uvicorn."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src directory is on the Python path so the retailernews package can be imported
SRC_PATH = Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from retailernews.api.app import app  # noqa: E402  (import after path setup)

__all__ = ("app",)
