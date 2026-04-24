"""CLI and library entry points for the comicbook workflow."""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

import httpx

from comicbook.config import AppConfig, load_config
from comicbook.db import ComicBookDB
from comicbook.deps import Deps
from comicbook.graph import run_workflow
from comicbook.state import RunState


def _positive_panel_count(raw: str) -> int:
    value = int(raw)
    if value < 1 or value > 12:
        raise argparse.ArgumentTypeError("--panels must be between 1 and 12")
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the supported comicbook workflow CLI arguments."""

    parser = argparse.ArgumentParser(prog="comicbook.run")
    parser.add_argument("user_prompt")
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--panels", type=_positive_panel_count)
    parser.add_argument("--budget-usd", type=float)
    parser.add_argument("--redact-prompts", action="store_true")
    return parser.parse_args(argv)


def _load_pricing(pricing_path: Path | None = None) -> dict[str, Any]:
    resolved = pricing_path or Path(__file__).with_name("pricing.json")
    return json.loads(resolved.read_text(encoding="utf-8"))


def _build_initial_state(
    user_prompt: str,
    *,
    run_id: str | None,
    dry_run: bool,
    force: bool,
    panels: int | None,
    budget_usd: float | None,
    redact_prompts: bool,
) -> RunState:
    return {
        "user_prompt": user_prompt,
        "run_id": run_id,
        "dry_run": dry_run,
        "force_regenerate": force,
        "exact_image_count": panels,
        "budget_usd": budget_usd,
        "redact_prompts": redact_prompts,
    }


def _build_runtime_deps(config: AppConfig, *, pricing_path: Path | None = None) -> tuple[Deps, ComicBookDB, httpx.Client]:
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
        pricing=_load_pricing(pricing_path),
        logger=logging.getLogger("comicbook.run"),
        pid_provider=os.getpid,
        hostname_provider=socket.gethostname,
    )
    return deps, db, http_client


def run_once(
    user_prompt: str,
    *,
    run_id: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    panels: int | None = None,
    budget_usd: float | None = None,
    redact_prompts: bool = False,
    deps: Deps | None = None,
    dotenv_path: str | Path = ".env",
) -> RunState:
    """Execute one workflow run from either tests or the CLI surface."""

    managed_db: ComicBookDB | None = None
    managed_http_client: httpx.Client | None = None
    runtime_deps = deps
    if runtime_deps is None:
        config = load_config(dotenv_path)
        runtime_deps, managed_db, managed_http_client = _build_runtime_deps(config)

    initial_state = _build_initial_state(
        user_prompt,
        run_id=run_id,
        dry_run=dry_run,
        force=force,
        panels=panels,
        budget_usd=budget_usd,
        redact_prompts=redact_prompts,
    )

    try:
        return run_workflow(initial_state, runtime_deps)
    finally:
        if managed_http_client is not None:
            managed_http_client.close()
        if managed_db is not None:
            managed_db.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the workflow from the command line."""

    args = parse_args(argv)
    final_state = run_once(
        args.user_prompt,
        run_id=args.run_id,
        dry_run=args.dry_run,
        force=args.force,
        panels=args.panels,
        budget_usd=args.budget_usd,
        redact_prompts=args.redact_prompts,
    )
    print(
        json.dumps(
            {
                "run_id": final_state["run_id"],
                "run_status": final_state["run_status"],
            }
        )
    )
    return 0 if final_state["run_status"] in {"succeeded", "partial", "dry_run"} else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["main", "parse_args", "run_once"]
