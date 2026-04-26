"""Persist annotated upload rows and record matching row results.

Rule recap: new template id inserts a fresh template row; an existing template id
updates the row in place and records a diff. Rows already marked invalid or
failed upstream are skipped here except for recording their terminal row result.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pipelines.shared.deps import Deps
from pipelines.workflows.template_upload.nodes import instrument_template_upload_node
from pipelines.workflows.template_upload.state import ImportRunState, TemplateImportRow, TemplateImportRowResult


def _format_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc) if value.tzinfo is not None else value
    rendered = normalized.replace(microsecond=0).isoformat()
    return rendered.replace("+00:00", "Z") if value.tzinfo is not None else f"{rendered}Z"


def _row_result_timestamp(deps: Deps) -> str:
    clock = getattr(deps, "clock", None)
    if callable(clock):
        return _format_timestamp(clock())
    return _format_timestamp(datetime.now(timezone.utc))


def _style_text_hash(style_text: str) -> str:
    return hashlib.sha256(style_text.encode("utf-8")).hexdigest()


def _style_text_preview(style_text: str, *, redact: bool) -> str:
    if redact:
        return f"sha256:{_style_text_hash(style_text)}"
    return style_text[:200]


def _field(record: Any, name: str) -> Any:
    if isinstance(record, dict):
        return record.get(name)
    return getattr(record, name)


def _has_terminal_result(row_index: int, row_results: list[TemplateImportRowResult]) -> bool:
    return any(result.get("row_index") == row_index and result.get("status") in {"failed", "skipped_resume"} for result in row_results)


def _append_and_record(
    *,
    deps: Deps,
    state: ImportRunState,
    row_results: list[TemplateImportRowResult],
    row: TemplateImportRow,
    result: TemplateImportRowResult,
    created_at: str,
    backfill_raw: str | None,
    persisted_supersedes_id: str | None,
    diff: dict[str, dict[str, object]] | None,
) -> None:
    row_results.append(result)
    deps.db.record_import_row_result(
        import_run_id=state["import_run_id"],
        source_file_hash=state["source_file_hash"],
        row_index=int(row["row_index"]),
        template_id=row.get("template_id"),
        status=result["status"],
        reason=result.get("reason"),
        warnings=list(result.get("warnings", [])),
        requested_supersedes_id=row.get("requested_supersedes_id"),
        persisted_supersedes_id=persisted_supersedes_id,
        diff=diff,
        backfill_raw=backfill_raw,
        retry_count=int(row.get("retry_count", 0)),
        created_at=created_at,
    )


def _compute_update_diff(row: TemplateImportRow, existing_record: Any, *, redact: bool) -> dict[str, dict[str, object]]:
    diff: dict[str, dict[str, object]] = {}

    comparisons = {
        "name": row.get("name"),
        "tags": row.get("tags"),
        "summary": row.get("summary"),
        "created_at": row.get("created_at"),
        "created_by_run": "workflow_import",
        "supersedes_id": row.get("resolved_supersedes_id"),
    }
    for field_name, after in comparisons.items():
        before = _field(existing_record, field_name)
        if before != after:
            diff[field_name] = {"before": before, "after": after}

    before_style_text = _field(existing_record, "style_text")
    after_style_text = row.get("style_text")
    if before_style_text != after_style_text:
        diff["style_text"] = {
            "before_preview": _style_text_preview(str(before_style_text), redact=redact),
            "after_preview": _style_text_preview(str(after_style_text), redact=redact),
        }

    before_hash = _field(existing_record, "style_text_hash") or _style_text_hash(str(before_style_text))
    after_hash = _style_text_hash(str(after_style_text))
    if before_hash != after_hash:
        diff["style_text_hash"] = {"before": before_hash, "after": after_hash}

    return diff


@instrument_template_upload_node(
    "upload_persist",
    complete_fields=lambda _state, delta: {
        "row_result_count": len(delta.get("row_results", [])),
        "deferred_row_count": len(delta.get("deferred_rows", [])),
    },
)
def upload_persist(state: ImportRunState, deps: Deps) -> dict[str, object]:
    """Persist rows serially according to write_mode and record row results."""

    parsed_rows = [dict(row) for row in list(state.get("parsed_rows") or [])]
    rows_to_process = sorted(int(index) for index in list(state.get("rows_to_process") or []))
    row_results = list(state.get("row_results") or [])
    dry_run = bool(state.get("dry_run", False))
    redact = bool(state.get("redact_style_text_in_logs", False))

    for row_index in rows_to_process:
        row = parsed_rows[row_index]
        if _has_terminal_result(row_index, row_results):
            continue

        created_at = str(row.get("created_at") or _row_result_timestamp(deps))
        warnings = list(row.get("warnings", []))
        persisted_supersedes_id = row.get("resolved_supersedes_id")
        if row.get("requested_supersedes_id") and persisted_supersedes_id is None:
            persisted_supersedes_id = None

        write_mode = row.get("write_mode")
        if write_mode == "defer":
            continue

        if write_mode == "skip":
            reason = ";".join(str(item) for item in row.get("validation_errors", []))
            result: TemplateImportRowResult = {
                "row_index": row_index,
                "template_id": row.get("template_id"),
                "status": "failed",
                "reason": reason,
                "warnings": warnings,
                "retry_count": int(row.get("retry_count", 0)),
            }
            _append_and_record(
                deps=deps,
                state=state,
                row_results=row_results,
                row=row,
                result=result,
                created_at=created_at,
                backfill_raw=row.get("backfill_raw"),
                persisted_supersedes_id=persisted_supersedes_id,
                diff=None,
            )
            continue

        existing_record = row.get("existing_record") or (
            deps.db.get_template_by_id(row.get("template_id")) if row.get("template_id") else None
        )
        diff = _compute_update_diff(row, existing_record, redact=redact) if write_mode == "update" and existing_record else None

        if dry_run:
            result = {
                "row_index": row_index,
                "template_id": row.get("template_id"),
                "status": "dry_run_ok",
                "reason": None,
                "warnings": warnings,
                "diff": diff,
                "retry_count": int(row.get("retry_count", 0)),
            }
            _append_and_record(
                deps=deps,
                state=state,
                row_results=row_results,
                row=row,
                result=result,
                created_at=created_at,
                backfill_raw=row.get("backfill_raw"),
                persisted_supersedes_id=persisted_supersedes_id,
                diff=diff,
            )
            continue

        try:
            if write_mode == "insert":
                deps.db.insert_template(
                    template_id=row["template_id"],
                    name=row["name"],
                    style_text=row["style_text"],
                    tags=list(row.get("tags") or []),
                    summary=row["summary"],
                    created_at=created_at,
                    created_by_run="workflow_import",
                    supersedes_id=persisted_supersedes_id,
                )
                result = {
                    "row_index": row_index,
                    "template_id": row.get("template_id"),
                    "status": "inserted",
                    "reason": None,
                    "warnings": warnings,
                    "retry_count": int(row.get("retry_count", 0)),
                }
                _append_and_record(
                    deps=deps,
                    state=state,
                    row_results=row_results,
                    row=row,
                    result=result,
                    created_at=created_at,
                    backfill_raw=row.get("backfill_raw"),
                    persisted_supersedes_id=persisted_supersedes_id,
                    diff=None,
                )
                continue

            if write_mode == "update":
                if diff == {}:
                    result = {
                        "row_index": row_index,
                        "template_id": row.get("template_id"),
                        "status": "skipped_duplicate",
                        "reason": None,
                        "warnings": warnings,
                        "retry_count": int(row.get("retry_count", 0)),
                    }
                    _append_and_record(
                        deps=deps,
                        state=state,
                        row_results=row_results,
                        row=row,
                        result=result,
                        created_at=created_at,
                        backfill_raw=row.get("backfill_raw"),
                        persisted_supersedes_id=persisted_supersedes_id,
                        diff=diff,
                    )
                    continue

                deps.db.update_template_in_place(
                    template_id=row["template_id"],
                    name=row["name"],
                    style_text=row["style_text"],
                    tags=list(row.get("tags") or []),
                    summary=row["summary"],
                    created_at=created_at,
                    created_by_run="workflow_import",
                    supersedes_id=persisted_supersedes_id,
                )
                result = {
                    "row_index": row_index,
                    "template_id": row.get("template_id"),
                    "status": "updated",
                    "reason": None,
                    "warnings": warnings,
                    "diff": diff,
                    "retry_count": int(row.get("retry_count", 0)),
                }
                _append_and_record(
                    deps=deps,
                    state=state,
                    row_results=row_results,
                    row=row,
                    result=result,
                    created_at=created_at,
                    backfill_raw=row.get("backfill_raw"),
                    persisted_supersedes_id=persisted_supersedes_id,
                    diff=diff,
                )
                continue

            raise ValueError(f"unsupported write_mode: {write_mode!r}")
        except Exception as exc:
            result = {
                "row_index": row_index,
                "template_id": row.get("template_id"),
                "status": "failed",
                "reason": f"db_error:{exc}",
                "warnings": warnings,
                "retry_count": int(row.get("retry_count", 0)),
            }
            _append_and_record(
                deps=deps,
                state=state,
                row_results=row_results,
                row=row,
                result=result,
                created_at=created_at,
                backfill_raw=row.get("backfill_raw"),
                persisted_supersedes_id=persisted_supersedes_id,
                diff=diff,
            )

    return {
        "row_results": row_results,
        "parsed_rows": parsed_rows,
    }


__all__ = ["upload_persist"]
