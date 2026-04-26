"""Reusable router transport helpers for structured Responses API calls."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from pipelines.shared.config import AppConfig
from pipelines.shared.responses import (
    ResponsesCallResult,
    ResponsesTransportError,
    call_structured_response as shared_call_structured_response,
)
from pipelines.workflows.image_prompt_gen.state import RouterPlan, TemplateSummary
from pipelines.workflows.image_prompt_gen.prompts.router_prompts import (
    ROUTER_ALLOWED_MODELS,
    ROUTER_RESPONSE_FORMAT,
    ROUTER_SYSTEM_PROMPT_V2,
    RouterValidationError,
    validate_router_plan,
)


class RouterPlanError(RuntimeError):
    """Raised when router output remains invalid after the allowed repair attempt."""


@dataclass(frozen=True, slots=True)
class RouterPlanResult:
    """Validated router plan plus metadata from one router invocation."""

    requested_model: str
    plan: RouterPlan
    raw_plan: str
    repair_attempts: int
    input_tokens: int
    output_tokens: int


def build_router_input_payload(
    *,
    user_prompt: str,
    known_templates: Sequence[TemplateSummary],
    exact_image_count: int | None,
    available_router_models: Sequence[str] = ROUTER_ALLOWED_MODELS,
) -> dict[str, Any]:
    """Build the router-visible JSON payload sent to the LLM."""

    constraints: dict[str, Any] = {
        "max_images": 12,
        "default_size": "1024x1536",
        "default_quality": "high",
        "allowed_sizes": ["1024x1024", "1024x1536", "1536x1024"],
        "allowed_qualities": ["low", "medium", "high", "auto"],
    }
    if exact_image_count is not None:
        constraints["exact_image_count"] = exact_image_count

    return {
        "user_prompt": user_prompt,
        "known_templates": [
            {
                "id": template.id,
                "name": template.name,
                "tags": list(template.tags),
                "summary": template.summary,
            }
            for template in known_templates
        ],
        "constraints": constraints,
        "available_router_models": list(available_router_models),
    }


def build_router_request_messages(
    router_input: Mapping[str, Any],
    *,
    validation_error: str | None = None,
    previous_response: str | None = None,
) -> list[dict[str, str]]:
    """Build the system/user message pair for the router call."""

    if validation_error is None:
        user_content = json.dumps(router_input, sort_keys=True)
    else:
        user_content = (
            "Your previous JSON response failed validation. Return corrected JSON only.\n\n"
            f"Original router input:\n{json.dumps(router_input, sort_keys=True)}\n\n"
            f"Validation error:\n{validation_error}\n\n"
            f"Previous invalid response:\n{previous_response or ''}"
        )

    return [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT_V2},
        {"role": "user", "content": user_content},
    ]


def call_structured_response(
    *,
    http_client: Any,
    config: AppConfig,
    model: str,
    response_format: Mapping[str, Any],
    messages: Sequence[Mapping[str, str]],
    transport: Any | None = None,
    timeout: float = 60.0,
) -> ResponsesCallResult:
    """Send one structured Responses API request with caller-provided messages/schema."""

    return shared_call_structured_response(
        http_client=http_client,
        config=config,
        model=model,
        response_format=response_format,
        messages=messages,
        transport=transport,
        timeout=timeout,
    )


def call_router_response(
    *,
    http_client: Any,
    config: AppConfig,
    model: str,
    router_input: Mapping[str, Any],
    transport: Any | None = None,
    validation_error: str | None = None,
    previous_response: str | None = None,
    timeout: float = 60.0,
) -> ResponsesCallResult:
    """Send one structured router request and return the extracted text plus usage."""

    return call_structured_response(
        http_client=http_client,
        config=config,
        model=model,
        response_format=ROUTER_RESPONSE_FORMAT,
        messages=build_router_request_messages(
            router_input,
            validation_error=validation_error,
            previous_response=previous_response,
        ),
        transport=transport,
        timeout=timeout,
    )


def _validate_requested_model(plan: RouterPlan, requested_model: str) -> None:
    if plan.router_model_chosen != requested_model:
        raise RouterValidationError(
            "Router response echoed a different router_model_chosen than the requested model: "
            f"requested {requested_model}, got {plan.router_model_chosen}"
        )


def request_router_plan(
    *,
    http_client: Any,
    config: AppConfig,
    model: str,
    router_input: Mapping[str, Any],
    available_templates: Sequence[TemplateSummary],
    exact_image_count: int | None,
    transport: Any | None = None,
) -> RouterPlanResult:
    """Request a validated router plan, allowing exactly one repair retry."""

    first_call = call_router_response(
        http_client=http_client,
        config=config,
        model=model,
        router_input=router_input,
        transport=transport,
    )

    try:
        plan = validate_router_plan(
            first_call.output_text,
            available_templates=available_templates,
            exact_image_count=exact_image_count,
        )
        _validate_requested_model(plan, model)
        return RouterPlanResult(
            requested_model=model,
            plan=plan,
            raw_plan=first_call.output_text,
            repair_attempts=0,
            input_tokens=first_call.input_tokens,
            output_tokens=first_call.output_tokens,
        )
    except RouterValidationError as first_error:
        repair_call = call_router_response(
            http_client=http_client,
            config=config,
            model=model,
            router_input=router_input,
            transport=transport,
            validation_error=str(first_error),
            previous_response=first_call.output_text,
        )
        try:
            repaired_plan = validate_router_plan(
                repair_call.output_text,
                available_templates=available_templates,
                exact_image_count=exact_image_count,
            )
            _validate_requested_model(repaired_plan, model)
        except RouterValidationError as repair_error:
            raise RouterPlanError(
                f"Router output remained invalid after one repair attempt on model {model}: {repair_error}"
            ) from repair_error

        return RouterPlanResult(
            requested_model=model,
            plan=repaired_plan,
            raw_plan=repair_call.output_text,
            repair_attempts=1,
            input_tokens=first_call.input_tokens + repair_call.input_tokens,
            output_tokens=first_call.output_tokens + repair_call.output_tokens,
        )


__all__ = [
    "RouterPlanError",
    "RouterPlanResult",
    "ResponsesCallResult",
    "ResponsesTransportError",
    "build_router_input_payload",
    "build_router_request_messages",
    "call_structured_response",
    "call_router_response",
    "request_router_plan",
]
