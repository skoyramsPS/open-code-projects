"""Choose insert, update, skip, or defer for upload rows."""

from __future__ import annotations

from typing import Any

from comicbook.deps import Deps
from comicbook.state import ImportRunState, TemplateImportRow


def _has_failed_result(row_index: int, row_results: list[dict[str, Any]]) -> bool:
    return any(result.get("row_index") == row_index and result.get("status") == "failed" for result in row_results)


def _future_same_run_template_ids(parsed_rows: list[TemplateImportRow], current_row_index: int) -> set[str]:
    future_ids: set[str] = set()
    for row in parsed_rows:
        row_index = row.get("row_index")
        template_id = row.get("template_id")
        if isinstance(row_index, int) and row_index > current_row_index and isinstance(template_id, str):
            future_ids.add(template_id)
    return future_ids


def _updated_row(row: TemplateImportRow, **changes: object) -> TemplateImportRow:
    updated = dict(row)
    updated.update(changes)
    return updated


def upload_decide_write_mode(state: ImportRunState, deps: Deps) -> dict[str, object]:
    """Annotate processable rows with their persistence mode."""

    parsed_rows = [dict(row) for row in list(state.get("parsed_rows") or [])]
    rows_to_process = list(state.get("rows_to_process") or [row.get("row_index") for row in parsed_rows])
    row_results = list(state.get("row_results") or [])
    deferred_rows: list[int] = []
    allow_defer = bool(state.get("allow_defer", True))

    for row_index in rows_to_process:
        row = parsed_rows[row_index]

        if row.get("validation_errors") or _has_failed_result(row_index, row_results):
            parsed_rows[row_index] = _updated_row(row, write_mode="skip")
            continue

        requested_supersedes_id = row.get("requested_supersedes_id")
        resolved_supersedes_id = row.get("resolved_supersedes_id")
        if allow_defer and isinstance(requested_supersedes_id, str) and resolved_supersedes_id is None:
            if deps.db.get_template_by_id(requested_supersedes_id) is not None:
                row = _updated_row(row, resolved_supersedes_id=requested_supersedes_id)
            elif requested_supersedes_id in _future_same_run_template_ids(parsed_rows, row_index):
                parsed_rows[row_index] = _updated_row(row, write_mode="defer")
                deferred_rows.append(row_index)
                continue

        template_id = row.get("template_id")
        existing_record = deps.db.get_template_by_id(template_id) if isinstance(template_id, str) else None
        if existing_record is not None:
            parsed_rows[row_index] = _updated_row(row, write_mode="update", existing_record=existing_record)
            continue

        parsed_rows[row_index] = _updated_row(row, write_mode="insert")

    return {
        "parsed_rows": parsed_rows,
        "deferred_rows": deferred_rows,
    }


__all__ = ["upload_decide_write_mode"]
