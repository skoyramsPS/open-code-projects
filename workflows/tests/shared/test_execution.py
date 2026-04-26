from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipelines.shared.config import AppConfig
from pipelines.shared.deps import Deps
from pipelines.shared.execution import bind_node, format_timestamp, pid_is_alive, prepare_initial_state, run_graph_with_lock


@dataclass
class FakeDB:
    acquire_calls: list[dict[str, object]] = field(default_factory=list)
    finalize_calls: list[dict[str, object]] = field(default_factory=list)
    run_record_status: str | None = None

    def acquire_run_lock(self, **kwargs: object) -> None:
        self.acquire_calls.append(kwargs)

    def get_run(self, run_id: str) -> SimpleNamespace | None:
        if self.run_record_status is None:
            return None
        return SimpleNamespace(run_id=run_id, status=self.run_record_status)

    def finalize_run(self, **kwargs: object) -> None:
        self.finalize_calls.append(kwargs)


@dataclass
class FakeGraph:
    result: dict[str, object] | None = None
    error: Exception | None = None
    invoked_with: dict[str, object] | None = None

    def invoke(self, state: dict[str, object]) -> dict[str, object]:
        self.invoked_with = state
        if self.error is not None:
            raise self.error
        return self.result or state


def make_deps(tmp_path: Path, *, db: object) -> Deps:
    config = AppConfig.model_validate(
        {
            "azure_openai_endpoint": "https://example.openai.azure.com",
            "azure_openai_api_key": "test-key",
            "azure_openai_api_version": "2025-04-01-preview",
            "azure_openai_chat_deployment": "gpt-5-router",
            "azure_openai_image_deployment": "gpt-image-1.5",
            "comicbook_router_prompt_version": "ROUTER_SYSTEM_PROMPT_V2",
        }
    )
    return Deps(
        config=config,
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 25, 12, 0, 1, tzinfo=timezone.utc),
        uuid_factory=lambda: "run-generated",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"image": {}},
        logger=logging.getLogger("test.execution"),
        pid_provider=lambda: 4321,
        hostname_provider=lambda: "host-a",
    )


def test_shared_execution_module_exposes_expected_helpers() -> None:
    assert callable(bind_node)
    assert callable(format_timestamp)
    assert callable(pid_is_alive)
    assert callable(prepare_initial_state)
    assert callable(run_graph_with_lock)


def test_bind_node_injects_deps(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, db=FakeDB())

    def node(state: dict[str, object], runtime_deps: Deps) -> dict[str, object]:
        return {"seen_run_id": state["run_id"], "same_deps": runtime_deps is deps}

    bound = bind_node(node, deps)

    assert bound({"run_id": "run-1"}) == {"seen_run_id": "run-1", "same_deps": True}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2026, 4, 25, 12, 0, 1), "2026-04-25T12:00:01Z"),
        (datetime(2026, 4, 25, 12, 0, 1, tzinfo=timezone.utc), "2026-04-25T12:00:01Z"),
    ],
)
def test_format_timestamp_renders_consistent_strings(value: datetime, expected: str) -> None:
    assert format_timestamp(value) == expected


def test_pid_is_alive_handles_expected_os_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipelines.shared.execution.os.kill", lambda pid, sig: None)
    assert pid_is_alive(123) is True

    def raise_process_lookup(pid: int, sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr("pipelines.shared.execution.os.kill", raise_process_lookup)
    assert pid_is_alive(123) is False

    def raise_permission(pid: int, sig: int) -> None:
        raise PermissionError

    monkeypatch.setattr("pipelines.shared.execution.os.kill", raise_permission)
    assert pid_is_alive(123) is True


def test_prepare_initial_state_uses_image_workflow_ingest_callable(tmp_path: Path) -> None:
    deps = make_deps(tmp_path, db=FakeDB())

    prepared = prepare_initial_state({"user_prompt": "  traveler portrait  "}, deps)

    assert prepared["run_id"] == "run-generated"
    assert prepared["user_prompt"] == "traveler portrait"
    assert prepared["started_at"] == "2026-04-25T12:00:01Z"
    assert prepared["dry_run"] is False


def test_run_graph_with_lock_returns_graph_result_and_acquires_lock(tmp_path: Path) -> None:
    fake_db = FakeDB()
    deps = make_deps(tmp_path, db=fake_db)
    graph = FakeGraph(result={"run_id": "run-generated", "status": "ok"})

    def graph_factory(runtime_deps: Deps) -> FakeGraph:
        assert runtime_deps is deps
        return graph

    result = run_graph_with_lock({"user_prompt": "traveler portrait"}, deps, graph_factory=graph_factory)

    assert result == {"run_id": "run-generated", "status": "ok"}
    assert graph.invoked_with is not None
    assert graph.invoked_with["run_id"] == "run-generated"
    assert fake_db.acquire_calls == [
        {
            "run_id": "run-generated",
            "user_prompt": "traveler portrait",
            "started_at": "2026-04-25T12:00:01Z",
            "pid": 4321,
            "host": "host-a",
            "router_prompt_version": "ROUTER_SYSTEM_PROMPT_V2",
            "pid_is_alive": pid_is_alive,
        }
    ]


def test_run_graph_with_lock_finalizes_running_record_on_failure(tmp_path: Path) -> None:
    fake_db = FakeDB(run_record_status="running")
    deps = make_deps(tmp_path, db=fake_db)
    graph = FakeGraph(error=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        run_graph_with_lock(
            {"user_prompt": "traveler portrait", "run_id": "run-123", "started_at": "2026-04-25T11:59:00Z"},
            deps,
            graph_factory=lambda runtime_deps: graph,
        )

    assert fake_db.finalize_calls == [
        {
            "run_id": "run-123",
            "ended_at": "2026-04-25T12:00:01Z",
            "status": "failed",
            "cache_hits": 0,
            "generated": 0,
            "failed": 0,
            "skipped_rate_limit": 0,
            "est_cost_usd": 0.0,
            "router_prompt_version": "ROUTER_SYSTEM_PROMPT_V2",
        }
    ]
