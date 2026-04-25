"""Compatibility wrapper for :mod:`pipelines.shared.runtime_deps`."""

from pipelines.shared.runtime_deps import (
    build_runtime_deps,
    close_managed_runtime_deps,
    load_pricing,
    resolve_runtime_deps,
)

__all__ = [
    "build_runtime_deps",
    "close_managed_runtime_deps",
    "load_pricing",
    "resolve_runtime_deps",
]
