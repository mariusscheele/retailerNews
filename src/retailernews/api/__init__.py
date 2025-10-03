"""API package for the Retailer News project."""

from __future__ import annotations

from .app import app, create_app  # noqa: F401
from .routes import router  # noqa: F401

__all__ = ["app", "create_app", "router"]
