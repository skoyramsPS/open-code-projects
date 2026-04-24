from __future__ import annotations

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
    responses: list[dict[str, Any]] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, *, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        if not self.responses:
            raise AssertionError("Image generation should not have been called")
        return self.responses.pop(0)


@pytest.fixture
def db(tmp_path: Path) -> ComicBookDB:
    database = ComicBookDB.connect(tmp_path / "comicbook.sqlite")
    try:
        yield database
    finally:
        database.close()


def make_config(*, daily_budget_usd: float | None = None) -> AppConfig:
    payload: dict[str, Any] = {
        "azure_openai_endpoint": "https://example.openai.azure.com",
        "azure_openai_api_key": "test-key",
        "azure_openai_api_version": "2025-04-01-preview",
        "azure_openai_chat_deployment": "gpt-5-router",
        "azure_openai_image_deployment": "gpt-image-1.5",
    }
    if daily_budget_usd is not None:
        payload["comicbook_daily_budget_usd"] = daily_budget_usd
    return AppConfig.model_validate(payload)


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
                                "rationale": "The panel count is straightforward and does not need escalation.",
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
        "usage": {"input_tokens": 45, "output_tokens": 18},
    }


def make_deps(
    tmp_path: Path,
    db: ComicBookDB,
    router_transport: FakeRouterTransport,
    image_transport: FakeImageTransport,
    *,
    pricing: dict[str, Any] | None = None,
    daily_budget_usd: float | None = None,
) -> Deps:
    return Deps(
        config=make_config(daily_budget_usd=daily_budget_usd),
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "generated-run-id",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing=pricing or {"image_models": {"gpt-image-1.5": {"usd_per_image": 0.0}}},
        logger=logging.getLogger("test-budget-guard"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        router_transport=router_transport,
        image_transport=image_transport,
    )


def test_run_workflow_stops_before_image_generation_when_run_budget_is_exceeded(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.graph import run_workflow

    router_transport = FakeRouterTransport(responses=[make_router_response("Single panel portrait.")])
    image_transport = FakeImageTransport()

    final_state = run_workflow(
        {
            "run_id": "run-budget-blocked",
            "user_prompt": "Create a single portrait panel.",
            "budget_usd": 0.5,
        },
        make_deps(
            tmp_path,
            db,
            router_transport,
            image_transport,
            pricing={"image_models": {"gpt-image-1.5": {"usd_per_image": 0.75}}},
        ),
    )

    assert final_state["run_status"] == "failed"
    assert final_state["summary"].generated == 0
    assert final_state["summary"].est_cost_usd == pytest.approx(0.75)
    assert len(image_transport.calls) == 0
    assert final_state["errors"][-1].code == "budget_guard"
    assert "0.50" in final_state["errors"][-1].message

    run_record = db.get_run("run-budget-blocked")
    assert run_record is not None
    assert run_record.status == "failed"
    assert run_record.est_cost_usd == pytest.approx(0.75)


def test_run_workflow_stops_before_image_generation_when_daily_budget_is_exceeded(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.graph import run_workflow

    seeded = db.acquire_run_lock(
        run_id="prior-run",
        user_prompt="Earlier run",
        started_at="2026-04-23T08:00:00Z",
        pid=101,
        host="host-a",
        router_prompt_version="ROUTER_SYSTEM_PROMPT_V2",
        pid_is_alive=lambda pid: True,
    )
    db.finalize_run(
        run_id=seeded.run_id,
        ended_at="2026-04-23T08:05:00Z",
        status="succeeded",
        cache_hits=0,
        generated=1,
        failed=0,
        skipped_rate_limit=0,
        est_cost_usd=0.8,
    )

    router_transport = FakeRouterTransport(responses=[make_router_response("Another portrait panel.")])
    image_transport = FakeImageTransport()

    final_state = run_workflow(
        {
            "run_id": "run-daily-budget-blocked",
            "user_prompt": "Create another portrait panel.",
        },
        make_deps(
            tmp_path,
            db,
            router_transport,
            image_transport,
            pricing={"image_models": {"gpt-image-1.5": {"usd_per_image": 0.3}}},
            daily_budget_usd=1.0,
        ),
    )

    assert final_state["run_status"] == "failed"
    assert final_state["summary"].generated == 0
    assert final_state["summary"].est_cost_usd == pytest.approx(0.3)
    assert len(image_transport.calls) == 0
    assert final_state["errors"][-1].code == "budget_guard"
    assert "daily budget" in final_state["errors"][-1].message.lower()


def test_run_once_dry_run_redacts_report_and_skips_image_generation(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.run import run_once

    router_transport = FakeRouterTransport(responses=[make_router_response("Panel one.")])
    image_transport = FakeImageTransport()
    deps = make_deps(tmp_path, db, router_transport, image_transport)

    final_state = run_once(
        "ULTRA SECRET USER PROMPT",
        run_id="run-dry",
        dry_run=True,
        redact_prompts=True,
        deps=deps,
    )

    assert final_state["run_status"] == "dry_run"
    assert final_state["summary"].generated == 0
    assert final_state["summary"].est_cost_usd == pytest.approx(0.0)
    assert image_transport.calls == []

    report_path = tmp_path / "runs" / "run-dry" / "report.md"
    summary_path = tmp_path / "logs" / "run-dry.summary.json"
    report_text = report_path.read_text(encoding="utf-8")
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "ULTRA SECRET USER PROMPT" not in report_text
    assert "ULTRA SECRET USER PROMPT" not in summary_text
    assert "sha256:" in report_text


def test_run_once_forwards_panels_constraint_to_router_and_generates_matching_prompt_count(
    tmp_path: Path,
    db: ComicBookDB,
) -> None:
    from comicbook.run import run_once

    router_transport = FakeRouterTransport(
        responses=[make_router_response("First panel.", "Second panel.")]
    )
    image_transport = FakeImageTransport(
        responses=[
            {"data": [{"b64_json": "aW1hZ2UtMQ=="}]},
            {"data": [{"b64_json": "aW1hZ2UtMg=="}]},
        ]
    )
    deps = make_deps(tmp_path, db, router_transport, image_transport)

    final_state = run_once(
        "Create exactly two comic panels.",
        run_id="run-panels",
        panels=2,
        deps=deps,
    )

    assert final_state["run_status"] == "succeeded"
    assert final_state["summary"].generated == 2
    assert len(image_transport.calls) == 2

    user_message = router_transport.calls[0]["payload"]["input"][1]
    router_input = json.loads(user_message["content"])
    assert router_input["constraints"]["exact_image_count"] == 2


def test_parse_args_accepts_required_runtime_flags() -> None:
    from comicbook.run import parse_args

    parsed = parse_args(
        [
            "Create exactly two comic panels.",
            "--run-id",
            "run-123",
            "--dry-run",
            "--force",
            "--panels",
            "2",
            "--budget-usd",
            "1.25",
            "--redact-prompts",
        ]
    )

    assert parsed.user_prompt == "Create exactly two comic panels."
    assert parsed.run_id == "run-123"
    assert parsed.dry_run is True
    assert parsed.force is True
    assert parsed.panels == 2
    assert parsed.budget_usd == pytest.approx(1.25)
    assert parsed.redact_prompts is True
