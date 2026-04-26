"""Skip rows that already completed successfully in a prior import run."""

from __future__ import annotations

from typing import Any

from pipelines.shared.deps import Deps
from pipelines.workflows.template_upload.nodes import instrument_template_upload_node
from pipelines.workflows.template_upload.state import ImportRunState, TemplateImportRow, TemplateImportRowResult

_TERMINAL_SUCCESS_STATUSES = {"inserted", "updated", "skipped_duplicate"}


def _field(record: object, name: str) -> object:
    if isinstance(record, dict):
        return record.get(name)
    return getattr(record, name)


def _with_retry_count(row: TemplateImportRow, retry_count: int) -> TemplateImportRow:
    updated = dict(row)
    updated["retry_count"] = retry_count
    return updated


@instrument_template_upload_node(
    "upload_resume_filter",
    complete_fields=lambda _state, delta: {
        "rows_to_process": len(delta.get("rows_to_process", [])),
        "rows_skipped_by_resume": len(delta.get("rows_skipped_by_resume", [])),
    },
)
def upload_resume_filter(state: ImportRunState, deps: Deps) -> dict[str, Any]:
    """Build the current run's worklist using prior terminal results for the same file hash."""

    source_file_hash = state.get("source_file_hash")
    if not source_file_hash:
        raise ValueError("upload_resume_filter requires state['source_file_hash']")

    parsed_rows = list(state.get("parsed_rows") or [])
    existing_row_results = list(state.get("row_results") or [])
    prior_results = deps.db.get_terminal_row_results_by_hash(source_file_hash)
    prior_by_row_index = {int(_field(result, "row_index")): result for result in prior_results}

    rows_to_process: list[int] = []
    rows_skipped_by_resume: list[int] = []
    updated_rows: list[TemplateImportRow] = []
    new_row_results: list[TemplateImportRowResult] = []

    for row in parsed_rows:
        row_index = int(row["row_index"])
        prior = prior_by_row_index.get(row_index)
        retry_count = int(_field(prior, "retry_count")) if prior is not None else 0
        updated_rows.append(_with_retry_count(row, retry_count))

        if prior is not None and _field(prior, "status") in _TERMINAL_SUCCESS_STATUSES:
            rows_skipped_by_resume.append(row_index)
            new_row_results.append(
                {
                    "row_index": row_index,
                    "template_id": row.get("template_id"),
                    "status": "skipped_resume",
                    "reason": "resume_success",
                }
            )
        else:
            rows_to_process.append(row_index)

    return {
        "parsed_rows": updated_rows,
        "rows_to_process": rows_to_process,
        "rows_skipped_by_resume": rows_skipped_by_resume,
        "row_results": existing_row_results + new_row_results,
    }


__all__ = ["upload_resume_filter"]
