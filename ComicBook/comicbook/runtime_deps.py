"""Legacy compatibility wrapper for :mod:`pipelines.shared.runtime_deps`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[2] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

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
