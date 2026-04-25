from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from pipelines.shared.config import AppConfig
from pipelines.shared.db import ComicBookDB
from pipelines.shared.deps import Deps


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


def make_router_response(*subjects: str) -> dict[str, Any]:
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
                                "rationale": "Panels can be rendered directly from the user request.",
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
                                    for subject in subjects
                                ],
                            }
                        ),
                    }
                ],
            }
        ],
        "usage": {"input_tokens": 90, "output_tokens": 30},
    }


def make_new_template_router_response() -> dict[str, Any]:
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
                                "rationale": "A fresh inky style should be stored and reused for this single panel.",
                                "needs_escalation": False,
                                "escalation_reason": None,
                                "template_decision": {
                                    "selected_template_ids": ["fresh-ink"],
                                    "extract_new_template": True,
                                    "new_template": {
                                        "id": "fresh-ink",
                                        "name": "Fresh Ink",
                                        "style_text": "Bold black ink lines with high-contrast cel shading.",
                                        "tags": ["ink", "comic"],
                                        "summary": "Bold inked comic shading for dramatic panels.",
                                        "supersedes_id": None,
                                    },
                                },
                                "prompts": [
                                    {
                                        "subject_text": "A lone ranger steps into a moonlit alley.",
                                        "template_ids": ["fresh-ink"],
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
        "usage": {"input_tokens": 60, "output_tokens": 25},
    }


def make_image_response(image_bytes: bytes) -> dict[str, Any]:
    return {
        "data": [
            {
                "b64_json": base64.b64encode(image_bytes).decode("ascii"),
            }
        ]
    }


def make_deps(
    tmp_path: Path,
    db: ComicBookDB,
    router_transport: FakeRouterTransport,
    image_transport: FakeImageTransport,
    *,
    pricing: dict[str, Any] | None = None,
    logger_name: str = "test-image-graph-scenarios",
) -> Deps:
    return Deps(
        config=make_config(),
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "generated-run-id",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing=pricing or {"image": {}},
        logger=logging.getLogger(logger_name),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        router_transport=router_transport,
        image_transport=image_transport,
    )
