"""Persist optional router-extracted templates before prompt materialization."""

from __future__ import annotations

from datetime import datetime, timezone

from comicbook.state import RouterPlan, RunState, TemplateSummary

from pipelines.shared.deps import Deps


def _format_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc) if value.tzinfo is not None else value
    rendered = normalized.replace(microsecond=0).isoformat()
    return rendered.replace("+00:00", "Z") if value.tzinfo is not None else f"{rendered}Z"


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _replace_plan_template_id(plan: RouterPlan, *, source_id: str, target_id: str) -> RouterPlan:
    if source_id == target_id:
        return plan

    payload = plan.model_dump()
    payload["template_decision"]["selected_template_ids"] = _dedupe_preserving_order(
        [target_id if template_id == source_id else template_id for template_id in payload["template_decision"]["selected_template_ids"]]
    )

    new_template = payload["template_decision"].get("new_template")
    if new_template is not None and new_template["id"] == source_id:
        new_template["id"] = target_id

    for prompt in payload["prompts"]:
        prompt["template_ids"] = _dedupe_preserving_order(
            [target_id if template_id == source_id else template_id for template_id in prompt["template_ids"]]
        )

    return RouterPlan.model_validate(payload)


def _to_template_summary(*, template_id: str, name: str, tags: list[str], summary: str, created_at: str) -> TemplateSummary:
    return TemplateSummary.model_validate(
        {
            "id": template_id,
            "name": name,
            "tags": tags,
            "summary": summary,
            "created_at": created_at,
        }
    )


def persist_template(state: RunState, deps: Deps) -> dict[str, object]:
    """Persist a router-extracted template and normalize later prompt references."""

    plan = state.get("plan")
    if plan is None:
        raise ValueError("persist_template requires state['plan']")

    if "templates" not in state:
        raise ValueError("persist_template requires state['templates']")

    run_id = state.get("run_id")
    if not run_id:
        raise ValueError("persist_template requires state['run_id']")

    if not plan.template_decision.extract_new_template:
        return {}

    draft = plan.template_decision.new_template
    if draft is None:
        raise ValueError("persist_template requires plan.template_decision.new_template when extraction is enabled")

    created_at = _format_timestamp(deps.clock())
    persisted = deps.db.insert_template(
        template_id=draft.id,
        name=draft.name,
        style_text=draft.style_text,
        tags=draft.tags,
        summary=draft.summary,
        created_at=created_at,
        created_by_run=run_id,
        supersedes_id=draft.supersedes_id,
    )

    updated_plan = _replace_plan_template_id(plan, source_id=draft.id, target_id=persisted.id)
    current_templates = list(state.get("templates", []))
    known_ids = {template.id for template in current_templates}
    if persisted.id in known_ids:
        updated_templates = current_templates
    else:
        updated_templates = current_templates + [
            _to_template_summary(
                template_id=persisted.id,
                name=persisted.name,
                tags=persisted.tags,
                summary=persisted.summary,
                created_at=persisted.created_at,
            )
        ]

    return {
        "plan": updated_plan,
        "templates": updated_templates,
    }


__all__ = ["persist_template"]
