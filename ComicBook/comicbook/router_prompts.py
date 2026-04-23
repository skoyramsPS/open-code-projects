"""Router prompt text, schema helpers, and deterministic template selection."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from comicbook.state import RouterPlan, TemplateSummary


ROUTER_SYSTEM_PROMPT_V2 = """You are the routing brain for a comic-book image generation workflow.
Return JSON only.

Decide which known templates to reuse, whether a reusable new template should be extracted,
and how many subject-focused prompt items to emit for the request.

Hard rules:
- follow the provided JSON schema exactly
- never invent a template id outside the supplied catalog, except for the new template id created in the same response
- keep rationale short and operator-friendly
- keep subject_text focused on subject content instead of repeating reusable style instructions
- use gpt-5.4-mini for straightforward requests and set needs_escalation=true only when gpt-5.4 should re-plan the same request
"""

ROUTER_PROMPT_VERSION = "ROUTER_SYSTEM_PROMPT_V2"
ROUTER_SYSTEM_PROMPT_LEAK_PREFIX = ROUTER_SYSTEM_PROMPT_V2[:40]
ROUTER_MAX_INLINE_TEMPLATES = 30
ROUTER_PREFILTER_LIMIT = 15
ROUTER_ALLOWED_MODELS = ("gpt-5.4", "gpt-5.4-mini")


class RouterValidationError(ValueError):
    """Raised when a router payload violates workflow-specific validation rules."""


ROUTER_PLAN_JSON_SCHEMA: dict[str, Any] = RouterPlan.model_json_schema(mode="validation")
ROUTER_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "comicbook_router_plan",
        "schema": deepcopy(ROUTER_PLAN_JSON_SCHEMA),
        "strict": True,
    },
}


def tokenize_for_overlap(text: str) -> set[str]:
    """Return lowercase lexical tokens used for deterministic pre-filter scoring."""

    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _prefilter_score(template: TemplateSummary, prompt_tokens: set[str]) -> int:
    haystack = " ".join([template.name, *template.tags, template.summary])
    return len(prompt_tokens.intersection(tokenize_for_overlap(haystack)))


def select_templates_for_router(user_prompt: str, templates: Sequence[TemplateSummary]) -> list[TemplateSummary]:
    """Return the deterministic subset of templates the router should see."""

    template_list = list(templates)
    if len(template_list) <= ROUTER_MAX_INLINE_TEMPLATES:
        return template_list

    prompt_tokens = tokenize_for_overlap(user_prompt)
    scored = [
        (
            _prefilter_score(template, prompt_tokens),
            template.created_at or "",
            template.id,
            template,
        )
        for template in template_list
    ]

    if all(score == 0 for score, *_rest in scored):
        newest = sorted(
            template_list,
            key=lambda template: (template.created_at or "", template.id),
            reverse=True,
        )
        return newest[:ROUTER_PREFILTER_LIMIT]

    ranked = sorted(scored, key=lambda item: item[2])
    ranked = sorted(ranked, key=lambda item: item[1], reverse=True)
    ranked = sorted(ranked, key=lambda item: item[0], reverse=True)
    return [template for *_prefix, template in ranked[:ROUTER_PREFILTER_LIMIT]]


def sanitize_rationale_text(rationale: str) -> str:
    """Apply the v1 rationale length and prompt-leak guard."""

    truncated = rationale[:600]
    if ROUTER_SYSTEM_PROMPT_LEAK_PREFIX and ROUTER_SYSTEM_PROMPT_LEAK_PREFIX in truncated:
        return "[redacted: potential prompt-leak]"
    return truncated


def _normalize_payload(raw_plan: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(raw_plan, str):
        try:
            payload = json.loads(raw_plan)
        except json.JSONDecodeError as exc:
            raise RouterValidationError(f"Router response was not valid JSON: {exc}") from exc
    else:
        payload = dict(raw_plan)

    if not isinstance(payload, dict):
        raise RouterValidationError("Router response must be a JSON object")

    rationale = payload.get("rationale")
    if isinstance(rationale, str):
        payload["rationale"] = sanitize_rationale_text(rationale)
    return payload


def _validate_template_usage(plan: RouterPlan, available_templates: Sequence[TemplateSummary]) -> None:
    available_ids = {template.id for template in available_templates}
    selected_ids = list(plan.template_decision.selected_template_ids)
    unknown_selected = [template_id for template_id in selected_ids if template_id not in available_ids]
    if unknown_selected:
        raise RouterValidationError(
            f"Router selected unknown template ids: {', '.join(sorted(unknown_selected))}"
        )

    prompt_allowed_ids = set(selected_ids)
    if plan.template_decision.new_template is not None:
        prompt_allowed_ids.add(plan.template_decision.new_template.id)

    unknown_prompt_template_ids = sorted(
        {
            template_id
            for item in plan.prompts
            for template_id in item.template_ids
            if template_id not in prompt_allowed_ids
        }
    )
    if unknown_prompt_template_ids:
        raise RouterValidationError(
            "Prompt items referenced template ids outside the selected subset: "
            + ", ".join(unknown_prompt_template_ids)
        )


def validate_router_plan(
    raw_plan: Mapping[str, Any] | str,
    *,
    available_templates: Sequence[TemplateSummary],
    exact_image_count: int | None = None,
) -> RouterPlan:
    """Parse and validate a router payload against workflow-specific rules."""

    payload = _normalize_payload(raw_plan)
    try:
        plan = RouterPlan.model_validate(payload)
    except ValidationError as exc:
        raise RouterValidationError(str(exc)) from exc

    if exact_image_count is not None and len(plan.prompts) != exact_image_count:
        raise RouterValidationError(
            f"Router plan prompt count {len(plan.prompts)} does not match exact_image_count={exact_image_count}"
        )

    _validate_template_usage(plan, available_templates)
    sanitized_rationale = sanitize_rationale_text(plan.rationale)
    if sanitized_rationale != plan.rationale:
        return plan.model_copy(update={"rationale": sanitized_rationale})
    return plan


__all__ = [
    "ROUTER_ALLOWED_MODELS",
    "ROUTER_MAX_INLINE_TEMPLATES",
    "ROUTER_PLAN_JSON_SCHEMA",
    "ROUTER_PREFILTER_LIMIT",
    "ROUTER_PROMPT_VERSION",
    "ROUTER_RESPONSE_FORMAT",
    "ROUTER_SYSTEM_PROMPT_LEAK_PREFIX",
    "ROUTER_SYSTEM_PROMPT_V2",
    "RouterValidationError",
    "sanitize_rationale_text",
    "select_templates_for_router",
    "tokenize_for_overlap",
    "validate_router_plan",
]
