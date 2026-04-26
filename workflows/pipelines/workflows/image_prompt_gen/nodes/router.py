"""Router node that requests, repairs, and escalates structured plan generation."""

from __future__ import annotations

from pipelines.shared.deps import Deps
from pipelines.shared.state import UsageTotals
from pipelines.workflows.image_prompt_gen.nodes import instrument_image_node
from pipelines.workflows.image_prompt_gen.state import RunState
from pipelines.workflows.image_prompt_gen.adapters.router_llm import build_router_input_payload, request_router_plan


def _available_router_models(deps: Deps) -> list[str]:
    models = [
        deps.config.comicbook_router_model_escalation,
        deps.config.comicbook_router_model_fallback,
    ]
    unique_models: list[str] = []
    for model in models:
        if model not in unique_models:
            unique_models.append(model)
    return unique_models


@instrument_image_node(
    "router",
    complete_fields=lambda _state, delta: {
        "router_model": delta.get("router_model"),
        "router_escalated": delta.get("router_escalated"),
        "prompt_count": len(getattr(delta.get("plan"), "prompts", [])),
        "repair_attempts": delta.get("plan_repair_attempts"),
    },
)
def router(state: RunState, deps: Deps) -> dict[str, object]:
    """Return the authoritative validated router plan for the current run."""

    user_prompt = state.get("user_prompt")
    if not user_prompt:
        raise ValueError("router requires state['user_prompt']")

    available_templates = list(state.get("templates_sent_to_router", []))
    exact_image_count = state.get("exact_image_count")
    router_input = build_router_input_payload(
        user_prompt=user_prompt,
        known_templates=available_templates,
        exact_image_count=exact_image_count,
        available_router_models=_available_router_models(deps),
    )

    initial_result = request_router_plan(
        http_client=deps.http_client,
        config=deps.config,
        model=deps.config.comicbook_router_model_fallback,
        router_input=router_input,
        available_templates=available_templates,
        exact_image_count=exact_image_count,
        transport=deps.router_transport,
    )

    authoritative_result = initial_result
    router_escalated = False
    if (
        initial_result.plan.needs_escalation
        and deps.config.comicbook_router_model_fallback == "gpt-5.4-mini"
        and deps.config.comicbook_router_model_escalation != deps.config.comicbook_router_model_fallback
    ):
        authoritative_result = request_router_plan(
            http_client=deps.http_client,
            config=deps.config,
            model=deps.config.comicbook_router_model_escalation,
            router_input=router_input,
            available_templates=available_templates,
            exact_image_count=exact_image_count,
            transport=deps.router_transport,
        )
        router_escalated = True

    existing_usage = UsageTotals.model_validate(state.get("usage") or {})
    total_router_calls = 1 + initial_result.repair_attempts
    total_input_tokens = initial_result.input_tokens
    total_output_tokens = initial_result.output_tokens
    total_repair_attempts = initial_result.repair_attempts

    if router_escalated:
        total_router_calls += 1 + authoritative_result.repair_attempts
        total_input_tokens += authoritative_result.input_tokens
        total_output_tokens += authoritative_result.output_tokens
        total_repair_attempts += authoritative_result.repair_attempts

    updated_usage = existing_usage.model_copy(
        update={
            "router_calls": existing_usage.router_calls + total_router_calls,
            "router_input_tokens": existing_usage.router_input_tokens + total_input_tokens,
            "router_output_tokens": existing_usage.router_output_tokens + total_output_tokens,
        }
    )

    return {
        "router_model": authoritative_result.plan.router_model_chosen,
        "plan": authoritative_result.plan,
        "plan_raw": authoritative_result.raw_plan,
        "plan_repair_attempts": total_repair_attempts,
        "router_escalated": router_escalated,
        "usage": updated_usage,
    }


__all__ = ["router"]
