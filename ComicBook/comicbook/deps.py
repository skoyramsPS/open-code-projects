"""Dependency container contracts."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from comicbook.config import AppConfig


class Filesystem(Protocol):
    """Optional filesystem abstraction for tests and future reuse."""

    def exists(self, path: Path) -> bool: ...

    def mkdir(self, path: Path, exist_ok: bool = True) -> None: ...

    def write_bytes(self, path: Path, data: bytes) -> int: ...


Clock = Callable[[], datetime]
UUIDFactory = Callable[[], str]
PidProvider = Callable[[], int]
HostnameProvider = Callable[[], str]


@dataclass(frozen=True, slots=True)
class Deps:
    """Explicit runtime collaborators shared by graph nodes.

    Optional transport and filesystem slots are reserved for tests so node logic
    stays dependency-injected and does not hide side effects behind globals.
    """

    config: AppConfig
    db: Any
    http_client: Any
    clock: Clock
    uuid_factory: UUIDFactory
    output_dir: Path
    runs_dir: Path
    logs_dir: Path
    pricing: Mapping[str, Any]
    logger: logging.Logger
    pid_provider: PidProvider
    hostname_provider: HostnameProvider
    router_transport: Any | None = None
    image_transport: Any | None = None
    filesystem: Filesystem | None = None


__all__ = [
    "Clock",
    "Deps",
    "Filesystem",
    "HostnameProvider",
    "PidProvider",
    "UUIDFactory",
]
