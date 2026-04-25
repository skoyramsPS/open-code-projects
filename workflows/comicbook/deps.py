"""Compatibility wrapper for :mod:`pipelines.shared.deps`."""

from pipelines.shared.deps import Clock, Deps, Filesystem, HostnameProvider, PidProvider, UUIDFactory

__all__ = [
    "Clock",
    "Deps",
    "Filesystem",
    "HostnameProvider",
    "PidProvider",
    "UUIDFactory",
]
