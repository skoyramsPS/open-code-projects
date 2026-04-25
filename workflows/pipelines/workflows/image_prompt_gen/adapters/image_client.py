"""Reusable single-image Azure client with bounded retry behavior."""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import httpx

from pipelines.shared.config import AppConfig


REQUEST_TIMEOUT_SECONDS = 600.0
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 120.0


@dataclass(frozen=True, slots=True)
class ImageClientResult:
    """Outcome of one prompt generation request."""

    ok: bool
    file_path: Path | None
    bytes_written: int
    attempts: int
    failure_code: str | None = None
    failure_reason: str | None = None
    last_http_status: int | None = None


def _build_image_url(config: AppConfig, image_model: str) -> str:
    return (
        f"{config.azure_openai_endpoint}/openai/deployments/{image_model}/images/generations"
        f"?api-version={config.azure_openai_api_version}"
    )


def _extract_error_details(response: httpx.Response) -> tuple[str, str]:
    fallback_message = response.text or f"HTTP {response.status_code}"

    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        return "http_error", fallback_message

    if not isinstance(payload, Mapping):
        return "http_error", fallback_message

    error = payload.get("error")
    if not isinstance(error, Mapping):
        return "http_error", fallback_message

    raw_code = str(error.get("code") or "http_error")
    message = str(error.get("message") or fallback_message)
    normalized_code = raw_code.lower()
    if normalized_code == "content_filter":
        return "content_filtered", message
    if response.status_code == 429:
        return "rate_limited", message
    if response.status_code == 408:
        return "request_timeout", message
    if 500 <= response.status_code < 600:
        return "server_error", message
    return normalized_code, message


def _retryable_status(status_code: int) -> bool:
    return status_code in {408, 429} or 500 <= status_code < 600


def _decode_image_bytes(response_json: Mapping[str, Any]) -> bytes:
    try:
        b64_payload = response_json["data"][0]["b64_json"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Image response missing data[0].b64_json") from exc

    if not isinstance(b64_payload, str) or not b64_payload:
        raise ValueError("Image response returned an empty b64_json payload")
    try:
        return base64.b64decode(b64_payload)
    except (ValueError, TypeError) as exc:
        raise ValueError("Image response b64_json payload could not be decoded") from exc


def generate_one(
    *,
    http_client: Any,
    config: AppConfig,
    prompt: str,
    size: str,
    quality: str,
    image_model: str,
    out_path: Path,
    transport: Any | None = None,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
    max_attempts: int = MAX_ATTEMPTS,
    retry_delay_seconds: float = RETRY_DELAY_SECONDS,
    sleep: Callable[[float], None] | None = None,
) -> ImageClientResult:
    """Generate one image, write it to disk, and return structured metadata."""

    url = _build_image_url(config, image_model)
    payload = {
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.azure_openai_api_key.get_secret_value()}",
    }
    sleep_fn = time.sleep if sleep is None else sleep

    for attempt in range(1, max_attempts + 1):
        try:
            if transport is not None:
                response_json = transport(url=url, headers=headers, payload=payload, timeout=timeout)
            else:
                response = http_client.post(url, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                response_json = response.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            failure_code, failure_reason = _extract_error_details(exc.response)
            if _retryable_status(status_code) and attempt < max_attempts:
                sleep_fn(retry_delay_seconds)
                continue
            return ImageClientResult(
                ok=False,
                file_path=None,
                bytes_written=0,
                attempts=attempt,
                failure_code=failure_code,
                failure_reason=failure_reason,
                last_http_status=status_code,
            )
        except (httpx.TimeoutException, httpx.TransportError, TimeoutError) as exc:
            if attempt < max_attempts:
                sleep_fn(retry_delay_seconds)
                continue
            return ImageClientResult(
                ok=False,
                file_path=None,
                bytes_written=0,
                attempts=attempt,
                failure_code="transport_error",
                failure_reason=str(exc),
                last_http_status=None,
            )
        except Exception as exc:
            return ImageClientResult(
                ok=False,
                file_path=None,
                bytes_written=0,
                attempts=attempt,
                failure_code="transport_error",
                failure_reason=str(exc),
                last_http_status=None,
            )

        if not isinstance(response_json, Mapping):
            return ImageClientResult(
                ok=False,
                file_path=None,
                bytes_written=0,
                attempts=attempt,
                failure_code="invalid_response",
                failure_reason="Image transport returned a non-object response",
                last_http_status=None,
            )

        try:
            image_bytes = _decode_image_bytes(response_json)
        except ValueError as exc:
            return ImageClientResult(
                ok=False,
                file_path=None,
                bytes_written=0,
                attempts=attempt,
                failure_code="invalid_response",
                failure_reason=str(exc),
                last_http_status=None,
            )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        bytes_written = out_path.write_bytes(image_bytes)
        return ImageClientResult(
            ok=True,
            file_path=out_path,
            bytes_written=bytes_written,
            attempts=attempt,
        )

    return ImageClientResult(
        ok=False,
        file_path=None,
        bytes_written=0,
        attempts=max_attempts,
        failure_code="transport_error",
        failure_reason="Image generation exhausted attempts without a terminal result",
        last_http_status=None,
    )


__all__ = [
    "ImageClientResult",
    "MAX_ATTEMPTS",
    "REQUEST_TIMEOUT_SECONDS",
    "RETRY_DELAY_SECONDS",
    "generate_one",
]
