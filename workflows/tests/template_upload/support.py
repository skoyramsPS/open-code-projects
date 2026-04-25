from __future__ import annotations

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


def make_deps(tmp_path: Path, db: ComicBookDB, *, router_transport: FakeRouterTransport | None = None) -> Deps:
    return Deps(
        config=make_config(),
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "generated-import-run-id",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"router_models": {"gpt-5.4-mini": {"usd_per_1k_input_tokens": 0.002, "usd_per_1k_output_tokens": 0.004}}},
        logger=logging.getLogger("test-template-upload"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        router_transport=router_transport,
    )


def make_backfill_response() -> dict[str, Any]:
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "tags": ["storybook", "warm", "painterly"],
                                "summary": "Soft painterly style with warm storybook lighting.",
                            }
                        ),
                    }
                ],
            }
        ],
        "usage": {"input_tokens": 120, "output_tokens": 30},
    }
