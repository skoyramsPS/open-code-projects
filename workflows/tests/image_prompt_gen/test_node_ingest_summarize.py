from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from pipelines.shared.state import UsageTotals
from pipelines.workflows.image_prompt_gen.state import ImageResult, RenderedPrompt, RouterPlan
from pipelines.shared.config import AppConfig
from pipelines.shared.db import ComicBookDB
from pipelines.shared.deps import Deps


@pytest.fixture
def db(tmp_path: Path) -> ComicBookDB:
    database = ComicBookDB.connect(tmp_path / "comicbook.sqlite")
    try:
        yield database
    finally:
        database.close()


def make_config() -> AppConfig:
    payload: dict[str, Any] = {
        "azure_openai_endpoint": "https://example.openai.azure.com",
        "azure_openai_api_key": "test-key",
        "azure_openai_api_version": "2025-04-01-preview",
        "azure_openai_chat_deployment": "gpt-5-router",
        "azure_openai_image_deployment": "gpt-image-1.5",
    }
    return AppConfig.model_validate(payload)


def make_deps(tmp_path: Path, db: ComicBookDB) -> Deps:
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
        logger=logging.getLogger("test-node-ingest-summarize"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
    )


def make_plan() -> RouterPlan:
    return RouterPlan.model_validate(
        {
            "router_model_chosen": "gpt-5.4-mini",
            "rationale": "The request is straightforward and fits a single panel.",
            "needs_escalation": False,
            "escalation_reason": None,
            "template_decision": {
                "selected_template_ids": [],
                "extract_new_template": False,
                "new_template": None,
            },
            "prompts": [
                {
                    "subject_text": "A heroic portrait at dawn.",
                    "template_ids": [],
                    "size": "1024x1536",
                    "quality": "high",
                    "image_model": "gpt-image-1.5",
                }
            ],
        }
    )


def test_target_tree_ingest_wrapper_fills_runtime_defaults_without_graph(tmp_path: Path, db: ComicBookDB) -> None:
    from pipelines.workflows.image_prompt_gen.nodes.ingest import ingest

    deps = make_deps(tmp_path, db)

    delta = ingest(
        {
            "user_prompt": "  A heroic portrait at dawn.  ",
            "dry_run": True,
            "force_regenerate": True,
            "exact_image_count": 1,
            "budget_usd": 1.5,
            "redact_prompts": True,
            "usage": {"router_calls": 2, "estimated_cost_usd": 0.25},
            "errors": [{"code": "warn", "message": "keep me"}],
            "image_results": [
                {"fingerprint": "fp-existing", "status": "failed", "failure_reason": "retry later"}
            ],
        },
        deps,
    )

    assert delta["run_id"] == "generated-run-id"
    assert delta["user_prompt"] == "A heroic portrait at dawn."
    assert delta["started_at"] == "2026-04-23T12:00:00Z"
    assert delta["dry_run"] is True
    assert delta["force_regenerate"] is True
    assert delta["exact_image_count"] == 1
    assert delta["budget_usd"] == pytest.approx(1.5)
    assert delta["redact_prompts"] is True
    assert isinstance(delta["usage"], UsageTotals)
    assert delta["usage"].router_calls == 2
    assert delta["usage"].estimated_cost_usd == pytest.approx(0.25)
    assert delta["errors"][0]["code"] == "warn"
    assert delta["image_results"][0]["fingerprint"] == "fp-existing"
    assert delta["rate_limit_consecutive_failures"] == 0


def test_target_tree_summarize_wrapper_writes_artifacts_and_finalizes_run_without_graph(tmp_path: Path, db: ComicBookDB) -> None:
    from pipelines.workflows.image_prompt_gen.nodes.summarize import summarize

    deps = make_deps(tmp_path, db)
    db.acquire_run_lock(
        run_id="run-direct-summary",
        user_prompt="SECRET USER PROMPT",
        started_at="2026-04-23T11:59:00Z",
        pid=123,
        host="host-a",
        router_prompt_version=deps.config.comicbook_router_prompt_version,
        pid_is_alive=lambda pid: True,
    )

    delta = summarize(
        {
            "run_id": "run-direct-summary",
            "started_at": "2026-04-23T11:59:00Z",
            "user_prompt": "SECRET USER PROMPT",
            "redact_prompts": True,
            "router_model": "gpt-5.4-mini",
            "router_escalated": False,
            "plan": make_plan(),
            "rendered_prompts": [
                RenderedPrompt(
                    fingerprint="fp-direct-summary",
                    subject_text="SECRET SUBJECT",
                    template_ids=[],
                    size="1024x1536",
                    quality="high",
                    image_model="gpt-image-1.5",
                    rendered_prompt="SECRET RENDERED PROMPT",
                )
            ],
            "cache_hits": [],
            "image_results": [
                ImageResult(
                    fingerprint="fp-direct-summary",
                    status="generated",
                    file_path=str(tmp_path / "image_output" / "run-direct-summary" / "fp-direct-summary.png"),
                    bytes=42,
                    run_id="run-direct-summary",
                    created_at="2026-04-23T12:00:00Z",
                )
            ],
            "usage": {"router_calls": 1, "image_calls": 1, "estimated_cost_usd": 0.75},
            "errors": [],
        },
        deps,
    )

    assert delta["run_status"] == "succeeded"
    assert delta["summary"].generated == 1
    assert delta["summary"].failed == 0
    assert delta["ended_at"] == "2026-04-23T12:00:00Z"

    report_path = tmp_path / "runs" / "run-direct-summary" / "report.md"
    summary_path = tmp_path / "logs" / "run-direct-summary.summary.json"
    assert report_path.exists()
    assert summary_path.exists()

    report_text = report_path.read_text(encoding="utf-8")
    assert "SECRET USER PROMPT" not in report_text
    assert "SECRET RENDERED PROMPT" not in report_text
    assert "sha256:" in report_text

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["run_status"] == "succeeded"
    assert summary_payload["usage"]["image_calls"] == 1
    assert summary_payload["rendered_prompts"][0]["status"] == "generated"
    assert summary_payload["rendered_prompts"][0]["rendered_prompt"].startswith("sha256:")

    run_record = db.get_run("run-direct-summary")
    assert run_record is not None
    assert run_record.status == "succeeded"
    assert run_record.generated == 1
    assert run_record.pid is None
    assert run_record.host is None
