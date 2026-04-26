"""Normalize raw upload rows into typed import-row state."""

from __future__ import annotations

from typing import Any

from pipelines.shared.deps import Deps
from pipelines.workflows.template_upload.nodes import instrument_template_upload_node
from pipelines.workflows.template_upload.state import ImportRunState, TemplateImportRow

_KNOWN_FIELDS = {
    "template_id",
    "name",
    "style_text",
    "tags",
    "summary",
    "created_at",
    "created_by_run",
    "supersedes_id",
}


def _base_row(row_index: int) -> TemplateImportRow:
    return {
        "row_index": row_index,
        "template_id": None,
        "name": None,
        "style_text": None,
        "tags": None,
        "summary": None,
        "created_at": None,
        "requested_supersedes_id": None,
        "resolved_supersedes_id": None,
        "validation_errors": [],
        "warnings": [],
        "needs_backfill_tags": False,
        "needs_backfill_summary": False,
        "backfill_raw": None,
        "write_mode": "skip",
        "retry_count": 0,
    }


def _normalize_text_field(
    row: dict[str, object],
    field_name: str,
    *,
    required: bool,
    validation_errors: list[str],
) -> str | None:
    if field_name not in row or row[field_name] is None:
        if required:
            validation_errors.append(f"missing_required_field:{field_name}")
        return None

    value = row[field_name]
    if not isinstance(value, str):
        validation_errors.append(f"invalid_field_type:{field_name}:str")
        return None

    normalized = value.strip()
    if required and not normalized:
        validation_errors.append(f"missing_required_field:{field_name}")
        return None
    return normalized or None


def _normalize_optional_tags(row: dict[str, object], validation_errors: list[str]) -> tuple[list[str] | None, bool]:
    if "tags" not in row or row["tags"] is None:
        return None, True

    raw_tags = row["tags"]
    if not isinstance(raw_tags, list):
        validation_errors.append("invalid_field_type:tags:list[str]")
        return None, False

    normalized_tags: list[str] = []
    for tag in raw_tags:
        if not isinstance(tag, str):
            validation_errors.append("invalid_field_type:tags:list[str]")
            return None, False
        normalized_tags.append(tag.strip())
    return normalized_tags, False


def _normalize_optional_summary(row: dict[str, object], validation_errors: list[str]) -> tuple[str | None, bool]:
    if "summary" not in row or row["summary"] is None:
        return None, True

    raw_summary = row["summary"]
    if not isinstance(raw_summary, str):
        validation_errors.append("invalid_field_type:summary:str")
        return None, False

    normalized = raw_summary.strip()
    if not normalized:
        return None, True
    return normalized, False


def _normalize_optional_string(
    row: dict[str, object],
    field_name: str,
    validation_errors: list[str],
) -> str | None:
    if field_name not in row or row[field_name] is None:
        return None

    value = row[field_name]
    if not isinstance(value, str):
        validation_errors.append(f"invalid_field_type:{field_name}:str")
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_row(raw_row: object, row_index: int) -> TemplateImportRow:
    parsed_row = _base_row(row_index)
    validation_errors = parsed_row["validation_errors"]
    warnings = parsed_row["warnings"]

    if not isinstance(raw_row, dict):
        validation_errors.append("row_must_be_object")
        return parsed_row

    for field_name in sorted(set(raw_row) - _KNOWN_FIELDS):
        warnings.append(f"unknown_field:{field_name}")

    if "created_by_run" in raw_row:
        warnings.append("ignored_field_override:created_by_run")

    parsed_row["template_id"] = _normalize_text_field(
        raw_row,
        "template_id",
        required=True,
        validation_errors=validation_errors,
    )
    parsed_row["name"] = _normalize_text_field(
        raw_row,
        "name",
        required=True,
        validation_errors=validation_errors,
    )
    parsed_row["style_text"] = _normalize_text_field(
        raw_row,
        "style_text",
        required=True,
        validation_errors=validation_errors,
    )

    tags, needs_backfill_tags = _normalize_optional_tags(raw_row, validation_errors)
    summary, needs_backfill_summary = _normalize_optional_summary(raw_row, validation_errors)
    parsed_row["tags"] = tags
    parsed_row["summary"] = summary
    parsed_row["needs_backfill_tags"] = needs_backfill_tags
    parsed_row["needs_backfill_summary"] = needs_backfill_summary
    parsed_row["created_at"] = _normalize_optional_string(raw_row, "created_at", validation_errors)
    parsed_row["requested_supersedes_id"] = _normalize_optional_string(raw_row, "supersedes_id", validation_errors)
    return parsed_row


@instrument_template_upload_node(
    "parse_and_validate",
    complete_fields=lambda _state, delta: {
        "parsed_row_count": len(delta.get("parsed_rows", [])),
        "validation_error_count": sum(len(row.get("validation_errors", [])) for row in delta.get("parsed_rows", [])),
    },
)
def parse_and_validate(state: ImportRunState, deps: Deps) -> dict[str, Any]:
    """Normalize each raw row and attach row-local validation metadata."""

    raw_rows = list(state.get("raw_rows") or [])
    max_rows = deps.config.comicbook_import_max_rows_per_file
    if len(raw_rows) > max_rows:
        raise ValueError(f"source exceeds max rows per file limit of {max_rows}")

    return {
        "parsed_rows": [_normalize_row(raw_row, row_index) for row_index, raw_row in enumerate(raw_rows)],
    }


__all__ = ["parse_and_validate"]
