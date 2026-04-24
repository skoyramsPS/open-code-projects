from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from comicbook.config import AppConfig
from comicbook.db import ComicBookDB
from comicbook.deps import Deps


@dataclass
class FakeRouterTransport:
    responses: list[dict[str, Any]]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, *, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        if not self.responses:
            raise AssertionError("No fake router responses remain")
        return self.responses.pop(0)


@dataclass
class FakeImageTransport:
    responses: list[dict[str, Any]]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, *, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        if not self.responses:
            raise AssertionError("No fake image responses remain")
        return self.responses.pop(0)


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


def make_router_response(subject: str) -> dict[str, Any]:
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "router_model_chosen": "gpt-5.4-mini",
                                "rationale": "One panel is enough for this request.",
                                "needs_escalation": False,
                                "escalation_reason": None,
                                "template_decision": {
                                    "selected_template_ids": [],
                                    "extract_new_template": False,
                                    "new_template": None,
                                },
                                "prompts": [
                                    {
                                        "subject_text": subject,
                                        "template_ids": [],
                                        "size": "1024x1536",
                                        "quality": "high",
                                        "image_model": "gpt-image-1.5",
                                    }
                                ],
                            }
                        ),
                    }
                ],
            }
        ],
        "usage": {"input_tokens": 40, "output_tokens": 15},
    }


def make_image_response(image_bytes: bytes) -> dict[str, Any]:
    return {
        "data": [
            {
                "b64_json": base64.b64encode(image_bytes).decode("ascii"),
            }
        ]
    }


def make_deps(tmp_path: Path, db: ComicBookDB, router_transport: FakeRouterTransport, image_transport: FakeImageTransport) -> Deps:
    return Deps(
        config=make_config(),
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "generated-run-id",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"image": {}},
        logger=logging.getLogger("test-graph-cache-hit"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        router_transport=router_transport,
        image_transport=image_transport,
    )


def test_run_workflow_second_run_uses_cache_and_skips_image_api(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.graph import run_workflow

    first_router_transport = FakeRouterTransport(responses=[make_router_response("Traveler portrait at sunrise.")])
    first_image_transport = FakeImageTransport(responses=[make_image_response(b"cached-image-source")])
    first_state = run_workflow(
        {
            "run_id": "run-1",
            "user_prompt": "Create one traveler portrait.",
        },
        make_deps(tmp_path, db, first_router_transport, first_image_transport),
    )

    assert first_state["summary"].generated == 1
    assert len(first_image_transport.calls) == 1

    second_router_transport = FakeRouterTransport(responses=[make_router_response("Traveler portrait at sunrise.")])
    second_image_transport = FakeImageTransport(responses=[])
    second_state = run_workflow(
        {
            "run_id": "run-2",
            "user_prompt": "Create one traveler portrait.",
        },
        make_deps(tmp_path, db, second_router_transport, second_image_transport),
    )

    assert second_state["run_status"] == "succeeded"
    assert second_state["summary"].cache_hits == 1
    assert second_state["summary"].generated == 0
    assert second_state["image_results"] == []
    assert second_state["usage"].router_calls == 1
    assert second_state["usage"].image_calls == 0
    assert len(second_router_transport.calls) == 1
    assert second_image_transport.calls == []

    second_run_record = db.get_run("run-2")
    assert second_run_record is not None
    assert second_run_record.status == "succeeded"
    assert second_run_record.cache_hits == 1
    assert second_run_record.generated == 0
