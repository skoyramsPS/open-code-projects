"""Shared runtime dependency construction helpers for CLI entry points."""

from __future__ import annotations

import json
import logging
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from comicbook.config import AppConfig, load_config
from comicbook.db import ComicBookDB
from comicbook.deps import Deps


def load_pricing(pricing_path: Path | None = None) -> dict[str, Any]:
    """Load the static model-pricing metadata used for best-effort cost estimates."""

    resolved = pricing_path or Path(__file__).with_name("pricing.json")
    return json.loads(resolved.read_text(encoding="utf-8"))


def build_runtime_deps(
    config: AppConfig,
    *,
    pricing_path: Path | None = None,
) -> tuple[Deps, ComicBookDB, httpx.Client]:
    """Create the managed runtime dependencies for one CLI-driven session."""

    db = ComicBookDB.connect(config.comicbook_db_path)
    http_client = httpx.Client()

    config.comicbook_image_output_dir.mkdir(parents=True, exist_ok=True)
    config.comicbook_runs_dir.mkdir(parents=True, exist_ok=True)
    config.comicbook_logs_dir.mkdir(parents=True, exist_ok=True)

    deps = Deps(
        config=config,
        db=db,
        http_client=http_client,
        clock=lambda: datetime.now(timezone.utc),
        uuid_factory=lambda: str(uuid4()),
        output_dir=config.comicbook_image_output_dir,
        runs_dir=config.comicbook_runs_dir,
        logs_dir=config.comicbook_logs_dir,
        pricing=load_pricing(pricing_path),
        logger=logging.getLogger("comicbook.run"),
        pid_provider=os.getpid,
        hostname_provider=socket.gethostname,
    )
    return deps, db, http_client


def resolve_runtime_deps(
    deps: Deps | None,
    *,
    dotenv_path: str | Path,
) -> tuple[Deps, ComicBookDB | None, httpx.Client | None]:
    """Reuse caller-provided deps or build managed ones from config."""

    runtime_deps = deps
    managed_db: ComicBookDB | None = None
    managed_http_client: httpx.Client | None = None
    if runtime_deps is None:
        config = load_config(dotenv_path)
        runtime_deps, managed_db, managed_http_client = build_runtime_deps(config)
    return runtime_deps, managed_db, managed_http_client


def close_managed_runtime_deps(
    managed_db: ComicBookDB | None,
    managed_http_client: httpx.Client | None,
) -> None:
    """Close only the runtime resources created for the current session."""

    if managed_http_client is not None:
        managed_http_client.close()
    if managed_db is not None:
        managed_db.close()


__all__ = [
    "build_runtime_deps",
    "close_managed_runtime_deps",
    "load_pricing",
    "resolve_runtime_deps",
]
