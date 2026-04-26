from __future__ import annotations

import pytest


def test_image_graph_module_exposes_expected_entry_points() -> None:
    from pipelines.workflows.image_prompt_gen.graph import build_workflow_graph
    from pipelines.workflows.image_prompt_gen.graph import run_workflow
    from pipelines.workflows.image_prompt_gen.graph import runtime_gate

    assert callable(build_workflow_graph)
    assert callable(run_workflow)
    assert callable(runtime_gate)


def test_image_run_module_uses_moved_graph_module(monkeypatch: pytest.MonkeyPatch) -> None:
    from pipelines.workflows.image_prompt_gen import graph as graph_module
    from pipelines.workflows.image_prompt_gen import run as run_module

    captured: list[tuple[dict[str, object], object]] = []

    def fake_run_workflow(initial_state: dict[str, object], deps: object) -> dict[str, object]:
        captured.append((dict(initial_state), deps))
        return {"run_id": "graph-run-1", "run_status": "succeeded"}

    monkeypatch.setattr(graph_module, "run_workflow", fake_run_workflow)

    result = run_module.run_workflow({"run_id": "graph-run-1", "user_prompt": "Traveler portrait"}, object())

    assert result == {"run_id": "graph-run-1", "run_status": "succeeded"}
    assert captured == [({"run_id": "graph-run-1", "user_prompt": "Traveler portrait"}, captured[0][1])]
