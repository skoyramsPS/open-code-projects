"""Normalize workflow input into the initial run state contract."""

from __future__ import annotations

from datetime import datetime, timezone

from comicbook.deps import Deps
from comicbook.state import RunState, UsageTotals


def _format_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc) if value.tzinfo is not None else value
    rendered = normalized.replace(microsecond=0).isoformat()
    return rendered.replace("+00:00", "Z") if value.tzinfo is not None else f"{rendered}Z"


def ingest(state: RunState, deps: Deps) -> dict[str, object]:
    """Fill the required ingest-phase state keys and runtime defaults."""

    user_prompt = state.get("user_prompt")
    if not user_prompt or not user_prompt.strip():
        raise ValueError("ingest requires state['user_prompt']")

    run_id = state.get("run_id") or deps.uuid_factory()
    if not run_id:
        raise ValueError("ingest could not determine a run_id")

    started_at = state.get("started_at") or _format_timestamp(deps.clock())
    usage = UsageTotals.model_validate(state.get("usage") or {})

    return {
        "run_id": run_id,
        "user_prompt": user_prompt.strip(),
        "dry_run": bool(state.get("dry_run", False)),
        "force_regenerate": bool(state.get("force_regenerate", False)),
        "exact_image_count": state.get("exact_image_count"),
        "budget_usd": state.get("budget_usd"),
        "redact_prompts": bool(state.get("redact_prompts", False)),
        "started_at": started_at,
        "usage": usage,
        "errors": list(state.get("errors", [])),
        "image_results": list(state.get("image_results", [])),
        "rate_limit_consecutive_failures": state.get("rate_limit_consecutive_failures", 0),
    }


__all__ = ["ingest"]
