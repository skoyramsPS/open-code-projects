"""Template-upload workflow nodes."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import wraps
from time import perf_counter
from typing import Any

from pipelines.shared.logging import log_node_event

_WORKFLOW = "template_upload"


def instrument_template_upload_node(
    node: str,
    *,
    start_fields: Callable[[Mapping[str, Any]], dict[str, Any]] | None = None,
    complete_fields: Callable[[Mapping[str, Any], Mapping[str, Any]], dict[str, Any]] | None = None,
) -> Callable[[Callable[[Mapping[str, Any], Any], dict[str, Any]]], Callable[[Mapping[str, Any], Any], dict[str, Any]]]:
    """Wrap a template-upload node with standard lifecycle logging."""

    def decorator(fn: Callable[[Mapping[str, Any], Any], dict[str, Any]]) -> Callable[[Mapping[str, Any], Any], dict[str, Any]]:
        @wraps(fn)
        def wrapped(state: Mapping[str, Any], deps: Any) -> dict[str, Any]:
            started = perf_counter()
            log_node_event(
                deps,
                state,
                "node_started",
                workflow=_WORKFLOW,
                node=node,
                **(start_fields(state) if start_fields is not None else {}),
            )
            try:
                delta = fn(state, deps)
            except Exception as exc:
                log_node_event(
                    deps,
                    state,
                    "node_failed",
                    level="ERROR",
                    workflow=_WORKFLOW,
                    node=node,
                    duration_ms=round((perf_counter() - started) * 1000, 3),
                    error={
                        "code": type(exc).__name__,
                        "message": str(exc),
                        "retryable": False,
                    },
                )
                raise

            completed_state = dict(state)
            completed_state.update(delta)
            fields = complete_fields(state, delta) if complete_fields is not None else {}
            log_node_event(
                deps,
                completed_state,
                "node_completed",
                workflow=_WORKFLOW,
                node=node,
                duration_ms=round((perf_counter() - started) * 1000, 3),
                **fields,
            )
            return delta

        return wrapped

    return decorator


__all__ = ["instrument_template_upload_node"]
