"""CLI and library entry points for the comicbook workflow."""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

import httpx

from comicbook.config import AppConfig, load_config
from comicbook.db import ComicBookDB
from comicbook.deps import Deps
from comicbook.graph import run_workflow
from comicbook.input_file import InputFileValidationError, InputPromptRecord, load_input_records
from comicbook.state import RunState


def _positive_panel_count(raw: str) -> int:
    value = int(raw)
    if value < 1 or value > 12:
        raise argparse.ArgumentTypeError("--panels must be between 1 and 12")
    return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the supported comicbook workflow CLI arguments."""

    parser = argparse.ArgumentParser(prog="comicbook.run")
    parser.add_argument("user_prompt", nargs="?")
    parser.add_argument("--input-file")
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--panels", type=_positive_panel_count)
    parser.add_argument("--budget-usd", type=float)
    parser.add_argument("--redact-prompts", action="store_true")
    args = parser.parse_args(argv)

    has_user_prompt = args.user_prompt is not None
    has_input_file = args.input_file is not None
    if has_user_prompt == has_input_file:
        parser.error("exactly one prompt source must be provided: positional user_prompt or --input-file")
    if has_input_file and args.run_id is not None:
        parser.error("--run-id cannot be used with --input-file")
    return args


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


def _resolve_runtime_deps(
    deps: Deps | None,
    *,
    dotenv_path: str | Path,
) -> tuple[Deps, ComicBookDB | None, httpx.Client | None]:
    runtime_deps = deps
    managed_db: ComicBookDB | None = None
    managed_http_client: httpx.Client | None = None
    if runtime_deps is None:
        config = load_config(dotenv_path)
        runtime_deps, managed_db, managed_http_client = _build_runtime_deps(config)
    return runtime_deps, managed_db, managed_http_client


def _close_managed_runtime_deps(
    managed_db: ComicBookDB | None,
    managed_http_client: httpx.Client | None,
) -> None:
    if managed_http_client is not None:
        managed_http_client.close()
    if managed_db is not None:
        managed_db.close()


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

    runtime_deps, managed_db, managed_http_client = _resolve_runtime_deps(
        deps,
        dotenv_path=dotenv_path,
    )

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
        _close_managed_runtime_deps(managed_db, managed_http_client)


def run_batch(
    records: Sequence[InputPromptRecord],
    *,
    input_file: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    panels: int | None = None,
    budget_usd: float | None = None,
    redact_prompts: bool = False,
    deps: Deps | None = None,
    dotenv_path: str | Path = ".env",
) -> dict[str, object]:
    """Execute a validated prompt batch serially through the single-run workflow."""

    runtime_deps, managed_db, managed_http_client = _resolve_runtime_deps(
        deps,
        dotenv_path=dotenv_path,
    )
    summary: dict[str, object] = {
        "input_file": None if input_file is None else str(input_file),
        "total_records": len(records),
        "succeeded": 0,
        "partial": 0,
        "dry_run": 0,
        "failed": 0,
        "run_ids": [],
    }
    run_ids: list[str] = []

    try:
        for index, record in enumerate(records, start=1):
            run_id = record.run_id or runtime_deps.uuid_factory()
            run_ids.append(run_id)
            runtime_deps.logger.info(
                "starting batch record %s/%s run_id=%s",
                index,
                len(records),
                run_id,
            )
            try:
                final_state = run_once(
                    record.user_prompt,
                    run_id=run_id,
                    dry_run=dry_run,
                    force=force,
                    panels=panels,
                    budget_usd=budget_usd,
                    redact_prompts=redact_prompts,
                    deps=runtime_deps,
                    dotenv_path=dotenv_path,
                )
            except Exception:
                summary["failed"] = int(summary["failed"]) + 1
                runtime_deps.logger.exception(
                    "batch record %s/%s run_id=%s failed",
                    index,
                    len(records),
                    run_id,
                )
                continue

            run_status = final_state["run_status"]
            if run_status == "succeeded":
                summary["succeeded"] = int(summary["succeeded"]) + 1
            elif run_status == "partial":
                summary["partial"] = int(summary["partial"]) + 1
            elif run_status == "dry_run":
                summary["dry_run"] = int(summary["dry_run"]) + 1
            else:
                summary["failed"] = int(summary["failed"]) + 1

            runtime_deps.logger.info(
                "completed batch record %s/%s run_id=%s status=%s",
                index,
                len(records),
                run_id,
                run_status,
            )

        summary["run_ids"] = run_ids
        return summary
    finally:
        _close_managed_runtime_deps(managed_db, managed_http_client)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the workflow from the command line."""

    args = parse_args(argv)
    if args.input_file is not None:
        try:
            records = load_input_records(args.input_file)
        except InputFileValidationError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        batch_summary = run_batch(
            records,
            input_file=args.input_file,
            dry_run=args.dry_run,
            force=args.force,
            panels=args.panels,
            budget_usd=args.budget_usd,
            redact_prompts=args.redact_prompts,
        )
        print(json.dumps(batch_summary))
        return 0 if int(batch_summary["failed"]) == 0 and int(batch_summary["partial"]) == 0 else 1

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


__all__ = ["main", "parse_args", "run_batch", "run_once"]
