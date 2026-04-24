from __future__ import annotations

import ast
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
                                "rationale": "A single portrait example can be satisfied with one panel.",
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
        "usage": {"input_tokens": 32, "output_tokens": 14},
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
        pricing={"image_models": {"gpt-image-1.5": {"usd_per_image": 0.0}}},
        logger=logging.getLogger("test-example-single-portrait"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        router_transport=router_transport,
        image_transport=image_transport,
    )


def test_single_portrait_example_runs_one_panel_with_shared_modules(tmp_path: Path, db: ComicBookDB) -> None:
    from examples.single_portrait_graph import run_single_portrait_workflow

    router_transport = FakeRouterTransport(responses=[make_router_response("Hero portrait in dramatic rim light.")])
    image_transport = FakeImageTransport(responses=[make_image_response(b"portrait-image")])

    final_state = run_single_portrait_workflow(
        {
            "run_id": "example-run",
            "user_prompt": "Create a hero portrait.",
            "exact_image_count": 4,
        },
        make_deps(tmp_path, db, router_transport, image_transport),
    )

    assert final_state["run_status"] == "succeeded"
    assert final_state["summary"].generated == 1
    assert len(final_state["rendered_prompts"]) == 1
    assert len(final_state["to_generate"]) == 1
    assert len(router_transport.calls) == 1
    assert len(image_transport.calls) == 1

    router_input = json.loads(router_transport.calls[0]["payload"]["input"][1]["content"])
    assert router_input["constraints"]["exact_image_count"] == 1

    run_record = db.get_run("example-run")
    assert run_record is not None
    assert run_record.status == "succeeded"


def test_shared_modules_do_not_import_workflow_specific_graph_or_run_modules() -> None:
    package_root = Path(__file__).resolve().parents[1] / "comicbook"
    offenders: list[str] = []

    for path in sorted(package_root.rglob("*.py")):
        if path.name in {"graph.py", "run.py"}:
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in {"comicbook.graph", "comicbook.run"}:
                        offenders.append(f"{path.relative_to(package_root.parent)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module in {"comicbook.graph", "comicbook.run"}:
                offenders.append(f"{path.relative_to(package_root.parent)} imports from {node.module}")

    assert offenders == []
