"""CLI and library entry points for the image prompt workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from pipelines.shared.deps import Deps
from pipelines.shared.logging import get_logger, log_event
from pipelines.shared.runtime_deps import close_managed_runtime_deps, resolve_runtime_deps
from pipelines.workflows.image_prompt_gen.input_file import InputFileValidationError, InputPromptRecord, load_input_records

LOGGER = get_logger(__name__)
WORKFLOW = "image_prompt_gen"
RunState = dict[str, object]


def run_workflow(initial_state: RunState, deps: Deps) -> RunState:
    from pipelines.workflows.image_prompt_gen.graph import run_workflow as workflow_run_workflow

    return workflow_run_workflow(initial_state, deps)


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

    runtime_deps, managed_db, managed_http_client = resolve_runtime_deps(
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

    log_event(
        LOGGER,
        "run_started",
        workflow=WORKFLOW,
        run_id=run_id,
        dry_run=dry_run,
        force_regenerate=force,
        exact_image_count=panels,
        message="Image workflow run started",
    )

    try:
        final_state = run_workflow(initial_state, runtime_deps)
        log_event(
            LOGGER,
            "run_completed",
            workflow=WORKFLOW,
            run_id=str(final_state.get("run_id") or run_id) if final_state.get("run_id") or run_id else None,
            run_status=final_state.get("run_status"),
            message="Image workflow run completed",
        )
        return final_state
    except Exception as exc:
        log_event(
            LOGGER,
            "run_failed",
            workflow=WORKFLOW,
            run_id=run_id,
            level="ERROR",
            message="Image workflow run failed",
            error_message=str(exc),
        )
        raise
    finally:
        close_managed_runtime_deps(managed_db, managed_http_client)


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

    runtime_deps, managed_db, managed_http_client = resolve_runtime_deps(
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
            log_event(
                LOGGER,
                "batch_record_started",
                workflow=WORKFLOW,
                run_id=run_id,
                batch_index=index,
                batch_total=len(records),
                input_file=None if input_file is None else str(input_file),
                message="Image batch record started",
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
            except Exception as exc:
                summary["failed"] = int(summary["failed"]) + 1
                log_event(
                    LOGGER,
                    "batch_record_failed",
                    workflow=WORKFLOW,
                    run_id=run_id,
                    batch_index=index,
                    batch_total=len(records),
                    input_file=None if input_file is None else str(input_file),
                    level="ERROR",
                    message="Image batch record failed",
                    error_message=str(exc),
                )
                continue

            run_status = str(final_state["run_status"])
            if run_status == "succeeded":
                summary["succeeded"] = int(summary["succeeded"]) + 1
            elif run_status == "partial":
                summary["partial"] = int(summary["partial"]) + 1
            elif run_status == "dry_run":
                summary["dry_run"] = int(summary["dry_run"]) + 1
            else:
                summary["failed"] = int(summary["failed"]) + 1

            log_event(
                LOGGER,
                "batch_record_completed",
                workflow=WORKFLOW,
                run_id=run_id,
                batch_index=index,
                batch_total=len(records),
                input_file=None if input_file is None else str(input_file),
                run_status=run_status,
                message="Image batch record completed",
            )

        summary["run_ids"] = run_ids
        log_event(
            LOGGER,
            "batch_completed",
            workflow=WORKFLOW,
            input_file=None if input_file is None else str(input_file),
            total_records=len(records),
            succeeded=int(summary["succeeded"]),
            partial=int(summary["partial"]),
            dry_run=int(summary["dry_run"]),
            failed=int(summary["failed"]),
            message="Image batch completed",
        )
        return summary
    finally:
        close_managed_runtime_deps(managed_db, managed_http_client)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the workflow from the command line."""

    args = parse_args(argv)
    if args.input_file is not None:
        try:
            records = load_input_records(args.input_file)
        except InputFileValidationError as exc:
            log_event(
                LOGGER,
                "input_file_validation_failed",
                workflow=WORKFLOW,
                level="ERROR",
                message="Input file validation failed",
                input_file=args.input_file,
                error_message=str(exc),
            )
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


__all__ = ["main", "parse_args", "run_batch", "run_once"]
