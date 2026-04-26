from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path

import pytest

from pipelines.shared.config import AppConfig
from pipelines.shared.deps import Deps
from pipelines.shared.logging import get_logger
from pipelines.shared.state import UsageTotals
from pipelines.workflows.image_prompt_gen.graph import run_workflow
from pipelines.workflows.image_prompt_gen.nodes.load_templates import load_templates

from .support import FakeImageTransport
from .support import FakeRouterTransport
from .support import db
from .support import make_deps
from .support import make_image_response
from .support import make_router_response


@pytest.fixture(autouse=True)
def reset_pipelines_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIPELINES_LOG_FORMAT", raising=False)
    monkeypatch.delenv("PIPELINES_LOG_LEVEL", raising=False)

    root = logging.getLogger("pipelines")
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    if hasattr(root, "_pipelines_logging_configured"):
        delattr(root, "_pipelines_logging_configured")
    root.setLevel(logging.NOTSET)
    root.propagate = True


def _node_payloads(output: str) -> list[dict[str, object]]:
    return [
        payload
        for payload in (json.loads(line) for line in output.splitlines() if line.strip())
        if payload["event"] in {"node_started", "node_completed", "node_failed"}
    ]


def test_run_workflow_emits_structured_node_logs(capsys: pytest.CaptureFixture[str], tmp_path: Path, db) -> None:
    router_transport = FakeRouterTransport(responses=[make_router_response("Traveler portrait at sunrise.")])
    image_transport = FakeImageTransport(responses=[make_image_response(b"image-one")])
    deps = replace(
        make_deps(tmp_path, db, router_transport, image_transport, logger_name="ignored-by-replace"),
        logger=get_logger("pipelines.workflows.image_prompt_gen.test_graph_logging"),
    )

    final_state = run_workflow(
        {
            "run_id": "run-log-1",
            "user_prompt": "Create one traveler portrait.",
        },
        deps,
    )

    payloads = _node_payloads(capsys.readouterr().out)

    assert final_state["run_status"] == "succeeded"
    assert payloads
    assert {payload["event"] for payload in payloads} == {"node_started", "node_completed"}
    assert {payload["node"] for payload in payloads} >= {
        "ingest",
        "load_templates",
        "router",
        "persist_template",
        "cache_lookup",
        "runtime_gate",
        "generate_images_serial",
        "summarize",
    }
    assert all(payload["workflow"] == "image_prompt_gen" for payload in payloads)
    assert all(payload["run_id"] == "run-log-1" for payload in payloads)
    assert all("node" in payload for payload in payloads)


def test_failing_image_node_emits_node_failed_log(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    deps = Deps(
        config=AppConfig.model_validate(
            {
                "azure_openai_endpoint": "https://example.openai.azure.com",
                "azure_openai_api_key": "test-key",
                "azure_openai_api_version": "2025-04-01-preview",
                "azure_openai_chat_deployment": "gpt-5-router",
                "azure_openai_image_deployment": "gpt-image-1.5",
            }
        ),
        db=object(),
        http_client=object(),
        clock=lambda: None,  # type: ignore[arg-type]
        uuid_factory=lambda: "run-generated",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"image": {}},
        logger=get_logger("pipelines.workflows.image_prompt_gen.test_node_failed"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
    )

    with pytest.raises(ValueError, match=r"requires state\['user_prompt'\]"):
        load_templates({"run_id": "run-log-2", "usage": UsageTotals()}, deps)

    payloads = _node_payloads(capsys.readouterr().out)

    assert [payload["event"] for payload in payloads] == ["node_started", "node_failed"]
    assert payloads[-1]["workflow"] == "image_prompt_gen"
    assert payloads[-1]["run_id"] == "run-log-2"
    assert payloads[-1]["node"] == "load_templates"
    assert payloads[-1]["error.code"] == "ValueError"
