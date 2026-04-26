"""Finalize upload results, persist import-run summary, and write artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pipelines.shared.deps import Deps
from pipelines.shared.state import UsageTotals
from pipelines.shared.execution import format_timestamp
from pipelines.workflows.template_upload.nodes import instrument_template_upload_node
from pipelines.workflows.template_upload.state import ImportRunState


def _counts(row_results: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(result.get("status")) for result in row_results)


def _warning_count(row_results: list[dict[str, Any]]) -> int:
    return sum(len(list(result.get("warnings", []))) for result in row_results)


def _backfilled_count(parsed_rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in parsed_rows if row.get("backfill_raw"))


def _final_run_status(*, state: ImportRunState, row_results: list[dict[str, Any]]) -> str:
    if state.get("dry_run", False):
        return "dry_run"
    if any(result.get("status") == "failed" for result in row_results):
        return "partial"
    return "succeeded"


def _row_result_table_line(result: dict[str, Any]) -> str:
    warnings = ", ".join(result.get("warnings", [])) or "-"
    reason = result.get("reason") or "-"
    return (
        f"| {result.get('row_index')} | {result.get('template_id') or '-'} | {result.get('status')} "
        f"| {reason} | {warnings} | {result.get('retry_count', 0)} |"
    )


def _updated_diff_sections(row_results: list[dict[str, Any]]) -> list[str]:
    sections: list[str] = []
    for result in row_results:
        if result.get("status") != "updated" or not result.get("diff"):
            continue
        sections.extend(["", f"## Updated row {result.get('row_index')} ({result.get('template_id')})", ""])
        for field_name, field_diff in dict(result["diff"]).items():
            sections.append(f"- {field_name}: {json.dumps(field_diff, sort_keys=True)}")
    return sections


def _unresolved_supersedes_section(row_results: list[dict[str, Any]]) -> list[str]:
    unresolved = [
        result
        for result in row_results
        if any(str(warning).startswith("missing_supersedes_target:") for warning in result.get("warnings", []))
    ]
    if not unresolved:
        return []

    lines = ["", "## Unresolved supersedes warnings", ""]
    for result in unresolved:
        warning_text = ", ".join(result.get("warnings", []))
        lines.append(f"- row {result.get('row_index')} ({result.get('template_id')}): {warning_text}")
    return lines


def _write_report(state: ImportRunState, deps: Deps, *, ended_at: str, run_status: str) -> Path:
    import_run_id = str(state["import_run_id"])
    usage = UsageTotals.model_validate(state.get("usage") or {})
    row_results = list(state.get("row_results") or [])
    parsed_rows = list(state.get("parsed_rows") or [])
    counts = _counts(row_results)

    report_dir = deps.runs_dir / import_run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    deps.logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "import_report.md"

    lines = [
        f"# Template Upload Report: {import_run_id}",
        "",
        "## Run Metadata",
        f"- Source: {state.get('source_label')}",
        f"- Source Hash: {state.get('source_file_hash')}",
        f"- Import Run ID: {import_run_id}",
        f"- Started: {state.get('started_at')}",
        f"- Ended: {ended_at}",
        f"- Status: {run_status}",
        "",
        "## Counts",
        f"- Total Rows: {len(parsed_rows)}",
        f"- Inserted: {counts.get('inserted', 0)}",
        f"- Updated: {counts.get('updated', 0)}",
        f"- Skipped Duplicate: {counts.get('skipped_duplicate', 0)}",
        f"- Skipped Resume: {counts.get('skipped_resume', 0)}",
        f"- Failed: {counts.get('failed', 0)}",
        f"- Backfilled: {_backfilled_count(parsed_rows)}",
        f"- Warnings: {_warning_count(row_results)}",
        f"- Estimated Backfill Cost USD: {usage.estimated_cost_usd:.6f}",
        "",
        "## Row Results",
        "",
        "| Row | Template ID | Status | Reason | Warnings | Retry Count |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(_row_result_table_line(result) for result in row_results)
    lines.extend(_updated_diff_sections(row_results))
    lines.extend(_unresolved_supersedes_section(row_results))
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _write_structured_log(state: ImportRunState, deps: Deps, *, ended_at: str, run_status: str) -> Path:
    import_run_id = str(state["import_run_id"])
    log_path = deps.logs_dir / f"{import_run_id}.import.jsonl"
    usage = UsageTotals.model_validate(state.get("usage") or {})
    deps.logs_dir.mkdir(parents=True, exist_ok=True)

    events: list[dict[str, Any]] = []
    for result in state.get("row_results", []):
        event_name = {
            "inserted": "template_inserted",
            "updated": "template_updated",
            "skipped_duplicate": "template_skipped_duplicate",
            "skipped_resume": "row_skipped_resume",
            "failed": "metadata_backfill_failed" if str(result.get("reason", "")).startswith("metadata_backfill_failed") else "row_failed",
            "dry_run_ok": "dry_run_row",
        }.get(str(result.get("status")), "row_result")
        events.append(
            {
                "import_run_id": import_run_id,
                "node": "upload_summarize",
                "event": event_name,
                "row_index": result.get("row_index"),
                "template_id": result.get("template_id"),
                "status": result.get("status"),
                "retry_count": result.get("retry_count", 0),
                "reason": result.get("reason"),
            }
        )

    events.append(
        {
            "import_run_id": import_run_id,
            "node": "upload_summarize",
            "event": "import_finished",
            "status": run_status,
            "ended_at": ended_at,
            "usage": usage.model_dump(mode="json"),
        }
    )
    log_path.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")
    return log_path


@instrument_template_upload_node(
    "upload_summarize",
    complete_fields=lambda _state, delta: {
        "run_status": delta.get("run_status"),
        "row_result_count": len(delta.get("row_results", [])),
    },
)
def upload_summarize(state: ImportRunState, deps: Deps) -> dict[str, object]:
    """Finalize import-run counts and write durable report artifacts."""

    import_run_id = state.get("import_run_id")
    if not import_run_id:
        raise ValueError("upload_summarize requires state['import_run_id']")
    started_at = state.get("started_at")
    if not started_at:
        raise ValueError("upload_summarize requires state['started_at']")

    row_results = list(state.get("row_results") or [])
    parsed_rows = list(state.get("parsed_rows") or [])
    usage = UsageTotals.model_validate(state.get("usage") or {})
    ended_at = format_timestamp(deps.clock())
    run_status = _final_run_status(state=state, row_results=row_results)
    counts = _counts(row_results)

    report_path = _write_report(state, deps, ended_at=ended_at, run_status=run_status)
    _write_structured_log(state, deps, ended_at=ended_at, run_status=run_status)
    deps.db.finalize_import_run(
        import_run_id=str(import_run_id),
        ended_at=ended_at,
        status=run_status,
        total_rows=len(parsed_rows),
        inserted=counts.get("inserted", 0),
        updated=counts.get("updated", 0),
        skipped_duplicate=counts.get("skipped_duplicate", 0),
        skipped_resume=counts.get("skipped_resume", 0),
        failed=counts.get("failed", 0),
        backfilled=_backfilled_count(parsed_rows),
        warnings=_warning_count(row_results),
        est_cost_usd=usage.estimated_cost_usd,
    )

    return {
        "ended_at": ended_at,
        "run_status": run_status,
        "report_path": str(report_path),
    }


__all__ = ["upload_summarize"]
