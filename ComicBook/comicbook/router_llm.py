"""Reusable router transport helpers for structured Responses API calls."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from comicbook.config import AppConfig
from comicbook.router_prompts import (
    ROUTER_ALLOWED_MODELS,
    ROUTER_RESPONSE_FORMAT,
    ROUTER_SYSTEM_PROMPT_V2,
    RouterValidationError,
    validate_router_plan,
)
from comicbook.state import RouterPlan, TemplateSummary


class RouterTransportError(RuntimeError):
    """Raised when the underlying router transport fails."""


class RouterPlanError(RuntimeError):
    """Raised when router output remains invalid after the allowed repair attempt."""


@dataclass(frozen=True, slots=True)
class RouterCallResult:
    """Single Responses API call result."""

    response_json: dict[str, Any]
    output_text: str
    input_tokens: int
    output_tokens: int


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


def extract_responses_output_text(response_json: Mapping[str, Any]) -> str:
    """Best-effort extraction of text output from the Responses API payload."""

    output = response_json.get("output", [])
    chunks: list[str] = []

    if isinstance(output, list):
        for item in output:
            if not isinstance(item, Mapping):
                continue

            direct_output_text = item.get("output_text")
            if isinstance(direct_output_text, str):
                chunks.append(direct_output_text)

            content = item.get("content", [])
            if not isinstance(content, list):
                continue

            for part in content:
                if not isinstance(part, Mapping):
                    continue
                text = part.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                    continue
                output_text = part.get("output_text")
                if isinstance(output_text, str):
                    chunks.append(output_text)

    if chunks:
        return "\n".join(chunk for chunk in chunks if chunk).strip()
    return json.dumps(response_json, sort_keys=True)


def extract_responses_usage(response_json: Mapping[str, Any]) -> tuple[int, int]:
    """Return input/output token counts when the provider includes them."""

    usage = response_json.get("usage", {})
    if not isinstance(usage, Mapping):
        return 0, 0

    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
    return int(input_tokens or 0), int(output_tokens or 0)


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
) -> RouterCallResult:
    """Send one structured router request and return the extracted text plus usage."""

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": ROUTER_RESPONSE_FORMAT,
        "input": build_router_request_messages(
            router_input,
            validation_error=validation_error,
            previous_response=previous_response,
        ),
    }
    url = f"{config.azure_openai_endpoint}/openai/responses?api-version={config.azure_openai_api_version}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.azure_openai_api_key.get_secret_value()}",
    }

    try:
        if transport is not None:
            response_json = transport(url=url, headers=headers, payload=payload, timeout=timeout)
        else:
            response = http_client.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            response_json = response.json()
    except Exception as exc:  # pragma: no cover - exercised by higher-level integration tests later
        raise RouterTransportError(f"Router transport failed for model {model}: {exc}") from exc

    if not isinstance(response_json, Mapping):
        raise RouterTransportError("Router transport returned a non-object response")

    output_text = extract_responses_output_text(response_json)
    input_tokens, output_tokens = extract_responses_usage(response_json)
    return RouterCallResult(
        response_json=dict(response_json),
        output_text=output_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
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
    "RouterCallResult",
    "RouterPlanError",
    "RouterPlanResult",
    "RouterTransportError",
    "build_router_input_payload",
    "build_router_request_messages",
    "call_router_response",
    "extract_responses_output_text",
    "extract_responses_usage",
    "request_router_plan",
]
