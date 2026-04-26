from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import replace
from pathlib import Path

import pytest

from pipelines.shared.config import AppConfig
from pipelines.shared.deps import Deps
from pipelines.shared.logging import get_logger
from pipelines.workflows.template_upload.graph import run_upload_workflow
from pipelines.workflows.template_upload.nodes.load_file import load_file

from .support import FakeRouterTransport
from .support import db
from .support import make_backfill_response
from .support import make_deps


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


def test_run_upload_workflow_emits_structured_node_logs(capsys: pytest.CaptureFixture[str], tmp_path: Path, db) -> None:
    payload = [{"template_id": "storybook-soft", "name": "Storybook Soft", "style_text": "Soft painterly linework."}]
    source_file = tmp_path / "templates.json"
    encoded = json.dumps(payload).encode("utf-8")
    source_file.write_bytes(encoded)
    import_run = db.acquire_import_lock(
        import_run_id="import-log-1",
        source_file_path=str(source_file),
        source_file_hash=hashlib.sha256(encoded).hexdigest(),
        started_at="2026-04-23T12:00:00Z",
        dry_run=False,
        pid=123,
        host="host-a",
        pid_is_alive=lambda pid: True,
    )
    deps = replace(
        make_deps(tmp_path, db, router_transport=FakeRouterTransport(responses=[make_backfill_response()])),
        logger=get_logger("pipelines.workflows.template_upload.test_graph_logging"),
    )

    final_state = run_upload_workflow(
        {
            "import_run_id": import_run.import_run_id,
            "source_file_path": str(source_file),
            "allow_external_path": True,
            "dry_run": False,
            "no_backfill": False,
            "allow_missing_optional": False,
            "budget_usd": None,
            "redact_style_text_in_logs": False,
            "started_at": import_run.started_at,
            "row_results": [],
            "errors": [],
            "usage": {},
        },
        deps,
    )

    payloads = _node_payloads(capsys.readouterr().out)

    assert final_state["run_status"] == "succeeded"
    assert payloads
    assert {payload["event"] for payload in payloads} == {"node_started", "node_completed"}
    assert {payload["node"] for payload in payloads} >= {
        "load_file",
        "parse_and_validate",
        "resume_filter",
        "backfill_metadata",
        "decide_write_mode",
        "persist",
        "summarize",
    }
    assert all(payload["workflow"] == "template_upload" for payload in payloads)
    assert all(payload["run_id"] == "import-log-1" for payload in payloads)
    assert all("node" in payload for payload in payloads)


def test_failing_template_upload_node_emits_node_failed_log(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
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
        uuid_factory=lambda: "import-generated",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"image": {}},
        logger=get_logger("pipelines.workflows.template_upload.test_node_failed"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
    )

    with pytest.raises(ValueError, match=r"requires exactly one of source_file_path or stdin_text"):
        load_file({"import_run_id": "import-log-2"}, deps)

    payloads = _node_payloads(capsys.readouterr().out)

    assert [payload["event"] for payload in payloads] == ["node_started", "node_failed"]
    assert payloads[-1]["workflow"] == "template_upload"
    assert payloads[-1]["run_id"] == "import-log-2"
    assert payloads[-1]["node"] == "load_file"
    assert payloads[-1]["error.code"] == "ValueError"
