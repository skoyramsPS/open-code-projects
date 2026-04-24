"""Prompt input-file parsing and validation helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


class InputFileValidationError(ValueError):
    """Raised when an input file cannot be parsed into prompt records."""


class InputPromptRecord(BaseModel):
    """Validated prompt input record for single-run execution."""

    model_config = ConfigDict(extra="forbid")

    user_prompt: str
    run_id: str | None = None

    @field_validator("user_prompt")
    @classmethod
    def validate_user_prompt(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("user_prompt must not be blank")
        return normalized

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            raise ValueError("run_id must not be blank when provided")
        return normalized


def _format_validation_error(error: dict[str, object]) -> str:
    location = ".".join(str(part) for part in error.get("loc", ()))
    error_type = str(error.get("type", ""))

    if error_type == "extra_forbidden":
        return f"unsupported field '{location}'"

    if error_type == "value_error":
        context = error.get("ctx") or {}
        inner_error = context.get("error")
        if inner_error is not None:
            return str(inner_error)

    message = str(error.get("msg", "invalid input record"))
    if location:
        return f"{location}: {message}"
    return message


def _validate_record(payload: dict[str, object], *, context: str) -> InputPromptRecord:
    try:
        return InputPromptRecord.model_validate(payload)
    except ValidationError as exc:
        detail = _format_validation_error(exc.errors()[0])
        raise InputFileValidationError(f"{context}: {detail}") from exc


def _check_duplicate_run_ids(records: list[InputPromptRecord], *, path: Path) -> None:
    seen: set[str] = set()
    for record in records:
        if record.run_id is None:
            continue
        if record.run_id in seen:
            raise InputFileValidationError(f"{path}: duplicate run_id '{record.run_id}'")
        seen.add(record.run_id)


def _load_json_records(path: Path) -> list[InputPromptRecord]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputFileValidationError(f"{path}: unable to read input file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputFileValidationError(f"{path}: invalid JSON: {exc.msg}") from exc

    if not isinstance(payload, list):
        raise InputFileValidationError(f"{path}: top-level JSON value must be a list")

    records: list[InputPromptRecord] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise InputFileValidationError(f"{path}: JSON record {index} must be an object")
        records.append(_validate_record(item, context=f"{path}: JSON record {index}"))

    _check_duplicate_run_ids(records, path=path)
    return records


def _load_csv_records(path: Path) -> list[InputPromptRecord]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise InputFileValidationError(f"{path}: CSV file must include a header row")

            fieldnames = [name.strip() for name in reader.fieldnames if name is not None]
            supported_columns = {"user_prompt", "run_id"}
            extra_columns = sorted(set(fieldnames) - supported_columns)
            if "user_prompt" not in fieldnames:
                raise InputFileValidationError(f"{path}: CSV file must include a user_prompt column")
            if extra_columns:
                quoted = ", ".join(extra_columns)
                raise InputFileValidationError(f"{path}: unsupported column(s): {quoted}")

            records: list[InputPromptRecord] = []
            for row_number, row in enumerate(reader, start=2):
                if None in row:
                    raise InputFileValidationError(f"{path}: row {row_number} has too many columns")

                normalized_row = {
                    key.strip(): value.strip() if isinstance(value, str) else value
                    for key, value in row.items()
                    if key is not None
                }
                records.append(_validate_record(normalized_row, context=f"{path}: CSV row {row_number}"))
    except OSError as exc:
        raise InputFileValidationError(f"{path}: unable to read input file: {exc}") from exc

    _check_duplicate_run_ids(records, path=path)
    return records


def load_input_records(path: str | Path) -> list[InputPromptRecord]:
    """Load prompt records from a JSON or CSV input file."""

    resolved = Path(path)
    suffix = resolved.suffix.lower()
    if suffix == ".json":
        return _load_json_records(resolved)
    if suffix == ".csv":
        return _load_csv_records(resolved)
    raise InputFileValidationError(f"{resolved}: unsupported input file extension '{resolved.suffix}'")


__all__ = ["InputFileValidationError", "InputPromptRecord", "load_input_records"]
