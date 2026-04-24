"""Summarize completed workflow state and finalize the persisted run."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from comicbook.deps import Deps
from comicbook.state import ImageResult, RenderedPrompt, RunState, RunSummary, UsageTotals


def _format_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc) if value.tzinfo is not None else value
    rendered = normalized.replace(microsecond=0).isoformat()
    return rendered.replace("+00:00", "Z") if value.tzinfo is not None else f"{rendered}Z"


def _collect_counts(image_results: list[ImageResult]) -> tuple[int, int, int]:
    generated = sum(1 for result in image_results if result.status == "generated")
    failed = sum(1 for result in image_results if result.status == "failed")
    skipped_rate_limit = sum(1 for result in image_results if result.status == "skipped_rate_limit")
    return generated, failed, skipped_rate_limit


def _determine_run_status(*, state: RunState, failed: int, skipped_rate_limit: int) -> str:
    if state.get("budget_blocked", False):
        return "failed"
    if state.get("dry_run", False):
        return "dry_run"
    if failed > 0 or skipped_rate_limit > 0:
        return "partial"
    return "succeeded"


def _redact_text(value: str, *, enabled: bool) -> str:
    if not enabled:
        return value
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _latest_image_path_for_fingerprint(fingerprint: str, deps: Deps) -> str | None:
    existing = deps.db.get_existing_images_by_fingerprint(fingerprint)
    for image in reversed(existing):
        if image.status == "generated" and image.file_path:
            return image.file_path
    return None


def _prompt_status(prompt: RenderedPrompt, state: RunState, deps: Deps, result_by_fingerprint: dict[str, ImageResult]) -> tuple[str, str | None]:
    fingerprint = prompt.fingerprint
    if fingerprint is None:
        return "unknown", None

    result = result_by_fingerprint.get(fingerprint)
    if result is not None:
        return result.status, result.file_path

    cache_hit_fingerprints = {item.fingerprint for item in state.get("cache_hits", [])}
    if fingerprint in cache_hit_fingerprints:
        return "cached", _latest_image_path_for_fingerprint(fingerprint, deps)

    if state.get("dry_run", False):
        return "planned", None
    if state.get("budget_blocked", False):
        return "blocked_budget", None
    return "pending", None


def _build_rendered_prompt_rows(state: RunState, deps: Deps) -> list[dict[str, object]]:
    redact = bool(state.get("redact_prompts", False))
    result_by_fingerprint = {result.fingerprint: result for result in state.get("image_results", [])}
    rows: list[dict[str, object]] = []

    for index, prompt in enumerate(state.get("rendered_prompts", []), start=1):
        status, file_path = _prompt_status(prompt, state, deps, result_by_fingerprint)
        rows.append(
            {
                "index": index,
                "fingerprint": prompt.fingerprint,
                "subject_text": _redact_text(prompt.subject_text, enabled=redact),
                "template_ids": list(prompt.template_ids),
                "rendered_prompt": _redact_text(prompt.rendered_prompt, enabled=redact),
                "status": status,
                "file_path": file_path,
            }
        )
    return rows


def _write_report_artifacts(state: RunState, deps: Deps, summary: RunSummary, usage: UsageTotals) -> None:
    run_id = summary.run_id
    redact = bool(state.get("redact_prompts", False))
    prompt_rows = _build_rendered_prompt_rows(state, deps)
    plan = state.get("plan")

    report_dir = deps.runs_dir / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    deps.logs_dir.mkdir(parents=True, exist_ok=True)

    report_lines = [
        f"# ComicBook Run Report: {run_id}",
        "",
        "## Run Metadata",
        f"- Status: {summary.run_status}",
        f"- Started: {summary.started_at}",
        f"- Ended: {summary.ended_at or 'n/a'}",
        f"- Original User Prompt: {_redact_text(state.get('user_prompt', ''), enabled=redact)}",
        f"- Router Model: {state.get('router_model') or 'n/a'}",
        f"- Router Escalated: {bool(state.get('router_escalated', False))}",
        f"- Cost Estimate USD: {summary.est_cost_usd:.2f}",
        "",
        "## Template Decision",
    ]

    if plan is not None:
        report_lines.extend(
            [
                f"- Rationale: {plan.rationale}",
                f"- Selected Template IDs: {', '.join(plan.template_decision.selected_template_ids) or 'none'}",
                f"- Extracted New Template: {plan.template_decision.extract_new_template}",
            ]
        )
        if plan.template_decision.new_template is not None:
            report_lines.extend(
                [
                    f"- New Template ID: {plan.template_decision.new_template.id}",
                    f"- New Template Name: {plan.template_decision.new_template.name}",
                    f"- New Template Summary: {plan.template_decision.new_template.summary}",
                ]
            )
    else:
        report_lines.append("- No router plan was captured.")

    report_lines.extend(["", "## Prompt Items"])
    if plan is not None:
        for index, prompt in enumerate(plan.prompts, start=1):
            report_lines.extend(
                [
                    f"### Prompt Item {index}",
                    f"- Subject Text: {_redact_text(prompt.subject_text, enabled=redact)}",
                    f"- Template IDs: {', '.join(prompt.template_ids) or 'none'}",
                    f"- Size: {prompt.size}",
                    f"- Quality: {prompt.quality}",
                    f"- Image Model: {prompt.image_model}",
                ]
            )
    else:
        report_lines.append("No prompt items were materialized.")

    report_lines.extend(["", "## Final Rendered Prompts"])
    for row in prompt_rows:
        report_lines.extend(
            [
                f"### Rendered Prompt {row['index']}",
                f"- Fingerprint: {row['fingerprint']}",
                f"- Subject Text: {row['subject_text']}",
                f"- Template IDs: {', '.join(row['template_ids']) or 'none'}",
                f"- Rendered Prompt: {row['rendered_prompt']}",
                f"- Status: {row['status']}",
                f"- File Path: {row['file_path'] or 'n/a'}",
            ]
        )

    report_lines.extend(
        [
            "",
            "## Summary",
            f"- Cache Hits: {summary.cache_hits}",
            f"- Generated: {summary.generated}",
            f"- Failed: {summary.failed}",
            f"- Skipped Rate Limit: {summary.skipped_rate_limit}",
            f"- Router Calls: {usage.router_calls}",
            f"- Image Calls: {usage.image_calls}",
        ]
    )

    if state.get("errors"):
        report_lines.extend(["", "## Errors"])
        for error in state["errors"]:
            report_lines.append(f"- {error.code}: {error.message}")

    (report_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary_payload = {
        "run_id": summary.run_id,
        "run_status": summary.run_status,
        "started_at": summary.started_at,
        "ended_at": summary.ended_at,
        "user_prompt": _redact_text(state.get("user_prompt", ""), enabled=redact),
        "router": {
            "model": state.get("router_model"),
            "escalated": bool(state.get("router_escalated", False)),
            "rationale": plan.rationale if plan is not None else None,
            "selected_template_ids": list(plan.template_decision.selected_template_ids) if plan is not None else [],
            "extract_new_template": plan.template_decision.extract_new_template if plan is not None else False,
        },
        "counts": {
            "cache_hits": summary.cache_hits,
            "generated": summary.generated,
            "failed": summary.failed,
            "skipped_rate_limit": summary.skipped_rate_limit,
        },
        "usage": usage.model_dump(mode="json"),
        "errors": [error.model_dump(mode="json") for error in state.get("errors", [])],
        "rendered_prompts": prompt_rows,
    }
    (deps.logs_dir / f"{run_id}.summary.json").write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def summarize(state: RunState, deps: Deps) -> dict[str, object]:
    """Finalize summary counters from state and persist the terminal run record."""

    run_id = state.get("run_id")
    if not run_id:
        raise ValueError("summarize requires state['run_id']")

    started_at = state.get("started_at")
    if not started_at:
        raise ValueError("summarize requires state['started_at']")

    usage = UsageTotals.model_validate(state.get("usage") or {})
    image_results = list(state.get("image_results", []))
    cache_hits = len(state.get("cache_hits", []))
    generated, failed, skipped_rate_limit = _collect_counts(image_results)
    run_status = _determine_run_status(state=state, failed=failed, skipped_rate_limit=skipped_rate_limit)
    ended_at = _format_timestamp(deps.clock())

    summary = RunSummary.model_validate(
        {
            "run_id": run_id,
            "run_status": run_status,
            "started_at": started_at,
            "ended_at": ended_at,
            "cache_hits": cache_hits,
            "generated": generated,
            "failed": failed,
            "skipped_rate_limit": skipped_rate_limit,
            "est_cost_usd": usage.estimated_cost_usd,
            "router_model": state.get("router_model"),
            "router_escalated": bool(state.get("router_escalated", False)),
        }
    )

    plan = state.get("plan")
    plan_json = plan.model_dump(mode="json") if plan is not None else None
    _write_report_artifacts(state, deps, summary, usage)
    deps.db.finalize_run(
        run_id=run_id,
        ended_at=ended_at,
        status=run_status,
        cache_hits=cache_hits,
        generated=generated,
        failed=failed,
        skipped_rate_limit=skipped_rate_limit,
        est_cost_usd=usage.estimated_cost_usd,
        router_model=state.get("router_model"),
        router_prompt_version=deps.config.comicbook_router_prompt_version,
        plan_json=plan_json,
    )

    return {
        "ended_at": ended_at,
        "summary": summary,
        "run_status": run_status,
    }


__all__ = ["summarize"]
