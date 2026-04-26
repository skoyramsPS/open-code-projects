from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from pipelines.workflows.image_prompt_gen.state import RenderedPrompt
from pipelines.shared.config import AppConfig
from pipelines.shared.db import ComicBookDB
from pipelines.shared.deps import Deps


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


@pytest.fixture
def db(tmp_path: Path) -> ComicBookDB:
    database = ComicBookDB.connect(tmp_path / "comicbook.sqlite")
    try:
        yield database
    finally:
        database.close()


def make_config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "azure_openai_endpoint": "https://example.openai.azure.com",
            "azure_openai_api_key": "test-key",
            "azure_openai_api_version": "2025-04-01-preview",
            "azure_openai_chat_deployment": "gpt-5-router",
            "azure_openai_image_deployment": "gpt-image-1.5",
        }
    )


def make_deps(tmp_path: Path, db: ComicBookDB, transport: FakeImageTransport) -> Deps:
    return Deps(
        config=make_config(),
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "run-1",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"image": {}},
        logger=logging.getLogger("test-node-generate-images-serial"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        image_transport=transport,
    )


def make_prompt(fingerprint: str, subject_text: str) -> RenderedPrompt:
    return RenderedPrompt.model_validate(
        {
            "fingerprint": fingerprint,
            "subject_text": subject_text,
            "template_ids": ["storybook-soft"],
            "size": "1024x1536",
            "quality": "high",
            "image_model": "gpt-image-1.5",
            "rendered_prompt": f"style text\n\n---\n\n{subject_text}",
        }
    )


def seed_prompts(db: ComicBookDB, prompts: list[RenderedPrompt]) -> None:
    for prompt in prompts:
        db.upsert_prompt_if_absent(
            prompt=prompt,
            first_seen_run="run-1",
            created_at="2026-04-23T12:00:00Z",
        )


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


def test_target_tree_generate_images_serial_wrapper_resumes_existing_file_and_generates_remaining_prompt(
    tmp_path: Path,
    db: ComicBookDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pipelines.workflows.image_prompt_gen.nodes.generate_images_serial import generate_images_serial
    from pipelines.workflows.image_prompt_gen.adapters import image_client

    monkeypatch.setattr(image_client.time, "sleep", lambda _: None)

    prompt_one = make_prompt("fp-1", "Traveler at dawn.")
    prompt_two = make_prompt("fp-2", "Traveler at dusk.")
    seed_prompts(db, [prompt_one, prompt_two])
    resumed_path = tmp_path / "image_output" / "run-1" / "fp-1.png"
    resumed_path.parent.mkdir(parents=True, exist_ok=True)
    resumed_path.write_bytes(b"existing-image")
    transport = FakeImageTransport(responses=[make_image_response(b"new-image")])

    delta = generate_images_serial(
        {
            "run_id": "run-1",
            "started_at": "2026-04-23T12:00:00Z",
            "to_generate": [prompt_one, prompt_two],
            "rendered_prompts_by_fp": {
                prompt_one.fingerprint: prompt_one,
                prompt_two.fingerprint: prompt_two,
            },
        },
        make_deps(tmp_path, db, transport),
    )

    assert [result.fingerprint for result in delta["image_results"]] == ["fp-1", "fp-2"]
    assert [result.status for result in delta["image_results"]] == ["generated", "generated"]
    assert delta["usage"].image_calls == 1
    assert delta["rate_limit_consecutive_failures"] == 0
    assert delta["errors"] == []
    assert len(transport.calls) == 1
    assert transport.calls[0]["payload"]["prompt"].endswith("Traveler at dusk.")

    resumed_rows = db.get_existing_images_by_fingerprint("fp-1")
    generated_rows = db.get_existing_images_by_fingerprint("fp-2")
    assert resumed_rows[-1].status == "generated"
    assert resumed_rows[-1].file_path == str(resumed_path)
    assert generated_rows[-1].status == "generated"
    assert generated_rows[-1].bytes == len(b"new-image")


def test_target_tree_generate_images_serial_wrapper_continues_after_non_retryable_failure(
    tmp_path: Path,
    db: ComicBookDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pipelines.workflows.image_prompt_gen.nodes.generate_images_serial import generate_images_serial
    from pipelines.workflows.image_prompt_gen.adapters import image_client

    monkeypatch.setattr(image_client.time, "sleep", lambda _: None)

    prompt_one = make_prompt("fp-1", "Blocked portrait.")
    prompt_two = make_prompt("fp-2", "Allowed portrait.")
    seed_prompts(db, [prompt_one, prompt_two])
    transport = FakeImageTransport(
        responses=[
            make_http_error(400, {"error": {"code": "content_filter", "message": "Blocked by policy."}}),
            make_image_response(b"allowed-image"),
        ]
    )

    delta = generate_images_serial(
        {
            "run_id": "run-1",
            "started_at": "2026-04-23T12:00:00Z",
            "to_generate": [prompt_one, prompt_two],
            "rendered_prompts_by_fp": {
                prompt_one.fingerprint: prompt_one,
                prompt_two.fingerprint: prompt_two,
            },
        },
        make_deps(tmp_path, db, transport),
    )

    assert [result.status for result in delta["image_results"]] == ["failed", "generated"]
    assert delta["usage"].image_calls == 2
    assert delta["rate_limit_consecutive_failures"] == 0
    assert len(delta["errors"]) == 1
    assert delta["errors"][0].code == "content_filtered"
    assert len(transport.calls) == 2

    first_rows = db.get_existing_images_by_fingerprint("fp-1")
    second_rows = db.get_existing_images_by_fingerprint("fp-2")
    assert first_rows[-1].status == "failed"
    assert "Blocked by policy." in (first_rows[-1].failure_reason or "")
    assert second_rows[-1].status == "generated"


def test_target_tree_generate_images_serial_wrapper_stops_after_two_consecutive_rate_limit_failures(
    tmp_path: Path,
    db: ComicBookDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pipelines.workflows.image_prompt_gen.nodes.generate_images_serial import generate_images_serial
    from pipelines.workflows.image_prompt_gen.adapters import image_client

    monkeypatch.setattr(image_client.time, "sleep", lambda _: None)

    prompt_one = make_prompt("fp-1", "First image.")
    prompt_two = make_prompt("fp-2", "Second image.")
    prompt_three = make_prompt("fp-3", "Third image.")
    seed_prompts(db, [prompt_one, prompt_two, prompt_three])
    transport = FakeImageTransport(
        responses=[
            make_http_error(429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests."}}),
            make_http_error(429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests."}}),
            make_http_error(429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests."}}),
            make_http_error(429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests."}}),
            make_http_error(429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests."}}),
            make_http_error(429, {"error": {"code": "rate_limit_exceeded", "message": "Too many requests."}}),
        ]
    )

    delta = generate_images_serial(
        {
            "run_id": "run-1",
            "started_at": "2026-04-23T12:00:00Z",
            "to_generate": [prompt_one, prompt_two, prompt_three],
            "rendered_prompts_by_fp": {
                prompt_one.fingerprint: prompt_one,
                prompt_two.fingerprint: prompt_two,
                prompt_three.fingerprint: prompt_three,
            },
        },
        make_deps(tmp_path, db, transport),
    )

    assert [result.status for result in delta["image_results"]] == ["failed", "failed", "skipped_rate_limit"]
    assert [result.fingerprint for result in delta["image_results"]] == ["fp-1", "fp-2", "fp-3"]
    assert delta["usage"].image_calls == 6
    assert delta["rate_limit_consecutive_failures"] == 2
    assert len(transport.calls) == 6
    assert len(delta["errors"]) == 3
    assert delta["errors"][0].code == "rate_limited"
    assert delta["errors"][1].code == "rate_limited"
    assert delta["errors"][2].code == "rate_limit_circuit_breaker"

    third_rows = db.get_existing_images_by_fingerprint("fp-3")
    assert third_rows[-1].status == "skipped_rate_limit"
    assert "circuit breaker" in (third_rows[-1].failure_reason or "").lower()
