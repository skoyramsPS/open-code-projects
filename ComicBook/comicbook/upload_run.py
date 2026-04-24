"""CLI and library entry points for the template-upload workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

from comicbook.db import RunLockError
from comicbook.execution import format_timestamp
from comicbook.run import _close_managed_runtime_deps, _resolve_runtime_deps
from comicbook.upload_graph import run_upload_workflow


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the supported template-upload CLI arguments."""

    parser = argparse.ArgumentParser(prog="comicbook.upload_run")
    parser.add_argument("source_file", nargs="?")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backfill", action="store_true")
    parser.add_argument("--allow-missing-optional", action="store_true")
    parser.add_argument("--budget-usd", type=float)
    parser.add_argument("--redact-style-text-in-logs", action="store_true")
    parser.add_argument("--allow-external-path", action="store_true")
    args = parser.parse_args(argv)

    has_source_file = args.source_file is not None
    has_stdin = bool(args.stdin)
    if has_source_file == has_stdin:
        parser.error("exactly one source must be provided: positional source_file or --stdin")
    if args.allow_missing_optional and not args.no_backfill:
        parser.error("--allow-missing-optional requires --no-backfill")
    return args


def _source_hash(*, source_file: str | Path | None, stdin_text: str | None) -> tuple[str, str | None]:
    if bool(source_file is not None) == bool(stdin_text is not None):
        raise ValueError("exactly one of source_file or stdin_text must be provided")

    if stdin_text is not None:
        encoded = stdin_text.encode("utf-8")
        return hashlib.sha256(encoded).hexdigest(), None

    source_path = Path(source_file).resolve()
    try:
        encoded = source_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read source file {source_path}: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest(), str(source_path)


def upload_templates(
    source_file: str | Path | None = None,
    *,
    stdin_text: str | None = None,
    dry_run: bool = False,
    no_backfill: bool = False,
    allow_missing_optional: bool = False,
    allow_external_path: bool = False,
    budget_usd: float | None = None,
    redact_style_text_in_logs: bool = False,
    deps=None,
    dotenv_path: str | Path = ".env",
):
    """Execute one template-upload workflow run from tests or the CLI surface."""

    runtime_deps, managed_db, managed_http_client = _resolve_runtime_deps(
        deps,
        dotenv_path=dotenv_path,
    )
    import_run_id: str | None = None
    started_at: str | None = None

    try:
        source_file_hash, resolved_source_path = _source_hash(source_file=source_file, stdin_text=stdin_text)
        import_run_id = runtime_deps.uuid_factory()
        started_at = format_timestamp(runtime_deps.clock())
        runtime_deps.db.acquire_import_lock(
            import_run_id=import_run_id,
            source_file_path=resolved_source_path,
            source_file_hash=source_file_hash,
            started_at=started_at,
            dry_run=dry_run,
            pid=runtime_deps.pid_provider(),
            host=runtime_deps.hostname_provider(),
            pid_is_alive=lambda pid: True,
        )

        return run_upload_workflow(
            {
                "import_run_id": import_run_id,
                "source_file_path": resolved_source_path,
                "stdin_text": stdin_text,
                "dry_run": dry_run,
                "no_backfill": no_backfill,
                "allow_missing_optional": allow_missing_optional,
                "allow_external_path": bool(
                    allow_external_path or runtime_deps.config.comicbook_import_allow_external_path
                ),
                "budget_usd": budget_usd,
                "redact_style_text_in_logs": redact_style_text_in_logs,
                "started_at": started_at,
                "row_results": [],
                "errors": [],
                "usage": {},
            },
            runtime_deps,
        )
    except Exception:
        if import_run_id is not None:
            record = runtime_deps.db.get_import_run(import_run_id)
            if record is not None and record.status == "running":
                runtime_deps.db.finalize_import_run(
                    import_run_id=import_run_id,
                    ended_at=format_timestamp(runtime_deps.clock()),
                    status="failed",
                )
        raise
    finally:
        _close_managed_runtime_deps(managed_db, managed_http_client)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the template-upload workflow from the command line."""

    try:
        args = parse_args(argv)
        stdin_text = sys.stdin.read() if args.stdin else None
        final_state = upload_templates(
            source_file=args.source_file,
            stdin_text=stdin_text,
            dry_run=args.dry_run,
            no_backfill=args.no_backfill,
            allow_missing_optional=args.allow_missing_optional,
            allow_external_path=args.allow_external_path,
            budget_usd=args.budget_usd,
            redact_style_text_in_logs=args.redact_style_text_in_logs,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except RunLockError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 5

    print(
        json.dumps(
            {
                "import_run_id": final_state["import_run_id"],
                "run_status": final_state["run_status"],
                "report_path": final_state.get("report_path"),
            }
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["main", "parse_args", "upload_templates"]
