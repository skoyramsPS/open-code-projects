"""Shared Responses API transport helpers used across workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from pipelines.shared.config import AppConfig


class ResponsesTransportError(RuntimeError):
    """Raised when the underlying Responses transport fails."""


@dataclass(frozen=True, slots=True)
class ResponsesCallResult:
    """Single Responses API call result."""

    response_json: dict[str, Any]
    output_text: str
    input_tokens: int
    output_tokens: int


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

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": dict(response_format),
        "input": [dict(message) for message in messages],
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
        raise ResponsesTransportError(f"Responses transport failed for model {model}: {exc}") from exc

    if not isinstance(response_json, Mapping):
        raise ResponsesTransportError("Responses transport returned a non-object response")

    output_text = extract_responses_output_text(response_json)
    input_tokens, output_tokens = extract_responses_usage(response_json)
    return ResponsesCallResult(
        response_json=dict(response_json),
        output_text=output_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


__all__ = [
    "ResponsesCallResult",
    "ResponsesTransportError",
    "call_structured_response",
    "extract_responses_output_text",
    "extract_responses_usage",
]
