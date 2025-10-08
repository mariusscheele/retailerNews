"""Utilities for working with the local blobstore used by the crawler."""

from __future__ import annotations

from pathlib import Path
from typing import Union

# ``retailernews/blobstore`` is part of the package so the storage lives alongside the
# code instead of under ``src/services``.  This keeps runtime artefacts encapsulated
# within the distributable module.
_PACKAGE_DIR = Path(__file__).resolve().parent

#: Name of the directory under :mod:`retailernews.blobstore` that contains the data.
DEFAULT_BLOB_SUBDIR = "data"

#: Default location where crawler artefacts are stored.
DEFAULT_BLOB_ROOT = _PACKAGE_DIR / DEFAULT_BLOB_SUBDIR


_Pathish = Union[str, Path]


def resolve_blob_root(blob_root: _Pathish | None = None) -> Path:
    """Return a :class:`Path` pointing at the blob root.

    ``blob_root`` may be either a string or :class:`Path`.  When ``None`` is
    provided, :data:`DEFAULT_BLOB_ROOT` is returned.  The path is not created on
    disk; callers can use :func:`ensure_blob_root` if they need to create it.
    """

    if blob_root is None:
        return DEFAULT_BLOB_ROOT
    if isinstance(blob_root, Path):
        return blob_root
    return Path(blob_root)


def ensure_blob_root(blob_root: _Pathish | None = None) -> Path:
    """Ensure the blob root exists and return it as a :class:`Path`."""

    root = resolve_blob_root(blob_root)
    root.mkdir(parents=True, exist_ok=True)
    return root


__all__ = [
    "DEFAULT_BLOB_ROOT",
    "DEFAULT_BLOB_SUBDIR",
    "ensure_blob_root",
    "resolve_blob_root",
]
