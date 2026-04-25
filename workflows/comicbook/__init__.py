"""Temporary compatibility package for legacy ``comicbook`` imports.

This package will grow during TG2 as modules move into ``pipelines`` while
preserving the legacy package-root convenience surface.
"""

from __future__ import annotations

from typing import Any

__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    if name == "upload_templates":
        from comicbook.upload_run import upload_templates

        return upload_templates
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["upload_templates", "__version__"]
