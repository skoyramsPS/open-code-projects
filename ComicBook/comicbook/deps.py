"""Legacy compatibility wrapper for :mod:`pipelines.shared.deps`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[2] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.shared.deps import Clock, Deps, Filesystem, HostnameProvider, PidProvider, UUIDFactory

__all__ = [
    "Clock",
    "Deps",
    "Filesystem",
    "HostnameProvider",
    "PidProvider",
    "UUIDFactory",
]
