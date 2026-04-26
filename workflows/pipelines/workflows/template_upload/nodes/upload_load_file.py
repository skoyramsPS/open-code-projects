"""Load template import input from disk or stdin."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pipelines.shared.deps import Deps
from pipelines.workflows.template_upload.nodes import instrument_template_upload_node
from pipelines.workflows.template_upload.state import ImportRunState


def _extract_json_error_snippet(text: str, position: int, radius: int = 40) -> str:
    start = max(0, position - radius)
    end = min(len(text), position + radius)
    return text[start:end].replace("\n", "\\n")


def _parse_payload(text: str) -> tuple[list[dict[str, object]], int]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = _extract_json_error_snippet(text, exc.pos)
        raise ValueError(
            f"invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}; near {snippet!r}"
        ) from exc

    if isinstance(payload, list):
        return payload, 1

    if isinstance(payload, dict):
        version = payload.get("version")
        templates = payload.get("templates")
        if version == 1 and isinstance(templates, list):
            return templates, 1

    raise ValueError("top-level JSON value must be an array or a version-1 envelope with a templates array")


def _allow_external_path(state: ImportRunState, deps: Deps) -> bool:
    return bool(state.get("allow_external_path", deps.config.comicbook_import_allow_external_path))


def _enforce_path_policy(resolved_path: Path, *, allow_external_path: bool) -> None:
    if allow_external_path:
        return

    allowed_root = Path.cwd().resolve()
    if not resolved_path.is_relative_to(allowed_root):
        raise ValueError(
            f"resolved path {resolved_path} is outside the allowed tree {allowed_root}; "
            "rerun with --allow-external-path to permit external files"
        )


def _read_source_bytes(state: ImportRunState) -> tuple[bytes, str | None, str]:
    stdin_text = state.get("stdin_text")
    source_file_path = state.get("source_file_path")

    if bool(stdin_text is not None) == bool(source_file_path):
        raise ValueError("upload_load_file requires exactly one of source_file_path or stdin_text")

    if stdin_text is not None:
        return stdin_text.encode("utf-8"), None, "<stdin>"

    resolved_path = Path(str(source_file_path)).resolve()
    try:
        data = resolved_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read source file {resolved_path}: {exc}") from exc
    return data, str(resolved_path), str(resolved_path)


@instrument_template_upload_node(
    "upload_load_file",
    complete_fields=lambda _state, delta: {
        "raw_row_count": len(delta.get("raw_rows", [])),
        "input_version": delta.get("input_version"),
        "source_label": delta.get("source_label"),
    },
)
def upload_load_file(state: ImportRunState, deps: Deps) -> dict[str, Any]:
    """Resolve, read, and parse the import source into raw rows."""

    source_file_path = state.get("source_file_path")
    if source_file_path is not None:
        _enforce_path_policy(
            Path(str(source_file_path)).resolve(),
            allow_external_path=_allow_external_path(state, deps),
        )

    raw_bytes, source_file_path, source_label = _read_source_bytes(state)
    max_file_bytes = deps.config.comicbook_import_max_file_bytes
    if len(raw_bytes) > max_file_bytes:
        raise ValueError(f"source exceeds max file bytes limit of {max_file_bytes}")

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"source must be valid UTF-8: {exc}") from exc

    raw_rows, input_version = _parse_payload(text)
    return {
        "source_file_path": source_file_path,
        "source_label": source_label,
        "source_file_hash": hashlib.sha256(raw_bytes).hexdigest(),
        "input_version": input_version,
        "raw_rows": raw_rows,
    }


__all__ = ["upload_load_file"]
