"""Shared structured-logging module for the pipelines package.

This module is the single home for logger construction and formatting in the
repository. Every workflow, node, and shared module logs through it.

The full standard, including required fields, level conventions, and adoption
expectations, lives in ``docs/standards/logging-standards.md``. Keep this
implementation aligned with that document; if you change behavior here, update
the standard in the same change.

Public surface:

- :func:`get_logger` — returns a logger configured with the shared formatter.
- :class:`JsonFormatter` — emits one JSON object per record with required fields.
- :class:`NodeLogContext` — small dataclass that captures workflow/run/node scope.
- :func:`log_node_event` — node-facing helper; resolves workflow/run_id from state.
- :func:`log_event` — non-node helper for shared modules and CLI entry points.

The module is stdlib-only by design.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

__all__ = [
    "JsonFormatter",
    "NodeLogContext",
    "get_logger",
    "log_event",
    "log_node_event",
]


# Field names that callers attach via ``extra=`` and the formatter promotes to
# top-level JSON keys. Keys not in this set are nested under ``extra`` so the
# top-level shape stays predictable.
_PROMOTED_FIELDS: tuple[str, ...] = (
    "event",
    "workflow",
    "run_id",
    "node",
    "component",
    "duration_ms",
)

_PROMOTED_ERROR_FIELDS: tuple[str, ...] = (
    "error.code",
    "error.message",
    "error.retryable",
)

_LOG_FORMAT_ENV = "PIPELINES_LOG_FORMAT"
_LOG_LEVEL_ENV = "PIPELINES_LOG_LEVEL"
_DEFAULT_LEVEL = logging.INFO
_HANDLER_FLAG = "_pipelines_logging_configured"


@dataclass(frozen=True, slots=True)
class NodeLogContext:
    """Scope captured for a single graph node invocation."""

    workflow: str
    run_id: str | None
    node: str | None = None


class JsonFormatter(logging.Formatter):
    """Format ``LogRecord`` objects as JSON lines.

    Required top-level fields are always present. Optional fields appear when
    populated. Unknown caller-supplied fields are nested under ``extra``.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - keep base signature
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc)
        payload: dict[str, Any] = {
            "timestamp": timestamp.isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage() or "log"),
            "workflow": getattr(record, "workflow", "shared"),
            "run_id": getattr(record, "run_id", None),
            "message": record.getMessage(),
        }
        for field in _PROMOTED_FIELDS:
            if field in ("event", "workflow", "run_id"):
                continue
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        error_payload = _extract_error_payload(record)
        payload.update(error_payload)

        extra_payload: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_KEYS:
                continue
            if key in _PROMOTED_FIELDS:
                continue
            if key == "error":
                if isinstance(value, Mapping):
                    remaining_error = {
                        nested_key: nested_value
                        for nested_key, nested_value in value.items()
                        if f"error.{nested_key}" not in _PROMOTED_ERROR_FIELDS
                    }
                    if remaining_error:
                        extra_payload[key] = remaining_error
                else:
                    extra_payload[key] = value
                continue
            extra_payload[key] = value
        if extra_payload:
            payload["extra"] = extra_payload

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=_json_default, separators=(",", ":"))


# Standard ``LogRecord`` attributes we never copy into ``extra``.
_RESERVED_RECORD_KEYS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


def _json_default(value: Any) -> Any:
    """Best-effort fallback for objects ``json.dumps`` cannot encode."""

    if isinstance(value, datetime):
        return value.isoformat()
    return repr(value)


def _extract_error_payload(record: logging.LogRecord) -> dict[str, Any]:
    error = getattr(record, "error", None)
    if not isinstance(error, Mapping):
        return {}

    payload: dict[str, Any] = {}
    for field_name in ("code", "message", "retryable"):
        value = error.get(field_name)
        if value is not None:
            payload[f"error.{field_name}"] = value
    return payload


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with the shared formatter and one stdout handler.

    Idempotent. Calling this many times for the same name does not duplicate
    handlers because configuration is keyed off the module-level flag on the
    root pipelines logger.
    """

    root = logging.getLogger("pipelines")
    if not getattr(root, _HANDLER_FLAG, False):
        _configure_root(root)
        setattr(root, _HANDLER_FLAG, True)
    return logging.getLogger(name)


def _configure_root(root: logging.Logger) -> None:
    level_name = os.environ.get(_LOG_LEVEL_ENV, "").upper()
    level = getattr(logging, level_name, _DEFAULT_LEVEL) if level_name else _DEFAULT_LEVEL
    root.setLevel(level)

    handler = logging.StreamHandler(stream=sys.stdout)
    text_mode = os.environ.get(_LOG_FORMAT_ENV, "").lower() == "text"
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        if text_mode
        else JsonFormatter()
    )
    root.addHandler(handler)
    root.propagate = False


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    workflow: str = "shared",
    run_id: str | None = None,
    level: str | int = "INFO",
    message: str | None = None,
    **fields: Any,
) -> None:
    """Emit one structured log line from non-node code.

    ``logger`` should come from :func:`get_logger`. ``event`` is the snake_case
    event name. Additional ``fields`` are attached as ``extra``; recognized
    promoted fields land at the top level of the JSON payload.
    """

    extra = {"event": event, "workflow": workflow, "run_id": run_id}
    extra.update(fields)
    logger.log(_resolve_level(level), message or event, extra=extra)


def log_node_event(
    deps: Any,
    state: Mapping[str, Any] | None,
    event: str,
    *,
    level: str | int = "INFO",
    message: str | None = None,
    node: str | None = None,
    workflow: str | None = None,
    **fields: Any,
) -> None:
    """Emit one structured log line from inside a graph node.

    Resolves ``workflow`` from the provided ``workflow`` keyword, the
    ``deps.workflow`` attribute (when present), or falls back to ``"unknown"``.
    Resolves ``run_id`` from ``state`` (``run_id`` or ``import_run_id``). Sets
    ``node`` from the provided keyword or, when omitted, infers it from the
    calling frame.
    """

    resolved_workflow = workflow or getattr(deps, "workflow", None) or "unknown"
    resolved_run_id: str | None = None
    if isinstance(state, Mapping):
        resolved_run_id = state.get("run_id") or state.get("import_run_id")  # type: ignore[assignment]

    if node is None:
        try:
            frame = sys._getframe(1)
            node = frame.f_code.co_name
        except (ValueError, AttributeError):
            node = None

    logger = getattr(deps, "logger", None) or get_logger(f"pipelines.workflows.{resolved_workflow}")
    extra = {
        "event": event,
        "workflow": resolved_workflow,
        "run_id": resolved_run_id,
        "node": node,
    }
    extra.update(fields)
    logger.log(_resolve_level(level), message or event, extra=extra)


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    return getattr(logging, level.upper(), _DEFAULT_LEVEL)
