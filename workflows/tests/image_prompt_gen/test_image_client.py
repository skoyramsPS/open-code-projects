from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from pipelines.workflows.image_prompt_gen.adapters.image_client import generate_one

from .support import make_config


@dataclass
class FakeImageTransport:
    responses: list[Any]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, *, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("No fake image responses remain")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_http_error(status_code: int, body: dict[str, Any]) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://example.openai.azure.com")
    response = httpx.Response(status_code, request=request, json=body)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)


def make_image_response(image_bytes: bytes) -> dict[str, Any]:
    return {
        "data": [
            {
                "b64_json": base64.b64encode(image_bytes).decode("ascii"),
            }
        ]
    }


def test_generate_one_retries_rate_limit_then_writes_image(tmp_path: Path) -> None:
    transport = FakeImageTransport(
        responses=[
            make_http_error(429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests."}}),
            make_image_response(b"png-bytes"),
        ]
    )

    result = generate_one(
        http_client=object(),
        config=make_config(),
        prompt="Heroic traveler at sunrise.",
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
        out_path=tmp_path / "image_output" / "run-1" / "fp-1.png",
        transport=transport,
        retry_delay_seconds=0.0,
        sleep=lambda _: None,
    )

    assert result.ok is True
    assert result.attempts == 2
    assert result.bytes_written == len(b"png-bytes")
    assert result.file_path == tmp_path / "image_output" / "run-1" / "fp-1.png"
    assert result.file_path.read_bytes() == b"png-bytes"

    assert len(transport.calls) == 2
    assert transport.calls[0]["url"] == (
        "https://example.openai.azure.com/openai/deployments/gpt-image-1.5/images/generations"
        "?api-version=2025-04-01-preview"
    )
    assert transport.calls[0]["payload"] == {
        "prompt": "Heroic traveler at sunrise.",
        "n": 1,
        "size": "1024x1536",
        "quality": "high",
    }


def test_generate_one_does_not_retry_content_filter_failure(tmp_path: Path) -> None:
    transport = FakeImageTransport(
        responses=[
            make_http_error(400, {"error": {"code": "content_filter", "message": "Prompt blocked by policy."}})
        ]
    )

    result = generate_one(
        http_client=object(),
        config=make_config(),
        prompt="Blocked prompt.",
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
        out_path=tmp_path / "image_output" / "run-1" / "blocked.png",
        transport=transport,
        retry_delay_seconds=0.0,
        sleep=lambda _: None,
    )

    assert result.ok is False
    assert result.attempts == 1
    assert result.failure_code == "content_filtered"
    assert result.last_http_status == 400
    assert "Prompt blocked by policy." in (result.failure_reason or "")
    assert len(transport.calls) == 1
    assert not (tmp_path / "image_output" / "run-1" / "blocked.png").exists()
