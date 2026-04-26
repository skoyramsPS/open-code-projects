"""Template upload workflow state and schema contracts."""

from __future__ import annotations

from typing import Literal, TypedDict

from pipelines.shared.state import RunStatus, UsageTotals, WorkflowError


ImportRowStatus = Literal["inserted", "updated", "failed", "skipped_resume", "skipped_duplicate", "dry_run_ok"]
ImportWriteMode = Literal["insert", "update", "skip", "defer"]


class TemplateImportRow(TypedDict, total=False):
    row_index: int
    template_id: str | None
    name: str | None
    style_text: str | None
    tags: list[str] | None
    summary: str | None
    created_at: str | None
    requested_supersedes_id: str | None
    resolved_supersedes_id: str | None
    validation_errors: list[str]
    warnings: list[str]
    needs_backfill_tags: bool
    needs_backfill_summary: bool
    backfill_raw: str | None
    write_mode: ImportWriteMode
    retry_count: int


class TemplateImportRowResult(TypedDict, total=False):
    row_index: int
    template_id: str | None
    status: ImportRowStatus
    reason: str | None
    warnings: list[str]
    diff: dict[str, dict[str, object]] | None
    retry_count: int


class ImportRunState(TypedDict, total=False):
    import_run_id: str
    source_file_path: str | None
    stdin_text: str | None
    source_label: str
    source_file_hash: str
    input_version: int
    dry_run: bool
    no_backfill: bool
    allow_missing_optional: bool
    allow_external_path: bool
    budget_usd: float | None
    redact_style_text_in_logs: bool
    started_at: str
    ended_at: str | None
    raw_rows: list[dict[str, object]]
    parsed_rows: list[TemplateImportRow]
    rows_to_process: list[int]
    deferred_rows: list[int]
    rows_skipped_by_resume: list[int]
    row_results: list[TemplateImportRowResult]
    usage: UsageTotals
    errors: list[WorkflowError]
    run_status: RunStatus
    report_path: str | None


__all__ = [
    "ImportRowStatus",
    "ImportRunState",
    "ImportWriteMode",
    "TemplateImportRow",
    "TemplateImportRowResult",
]
