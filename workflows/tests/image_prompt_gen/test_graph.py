from __future__ import annotations

import pytest


def test_target_tree_wrapper_points_to_image_graph_module() -> None:
    from comicbook.graph import build_workflow_graph as wrapped_build_workflow_graph
    from comicbook.graph import run_workflow as wrapped_run_workflow
    from comicbook.graph import runtime_gate as wrapped_runtime_gate
    from pipelines.workflows.image_prompt_gen.graph import build_workflow_graph
    from pipelines.workflows.image_prompt_gen.graph import run_workflow
    from pipelines.workflows.image_prompt_gen.graph import runtime_gate

    assert wrapped_build_workflow_graph is build_workflow_graph
    assert wrapped_run_workflow is run_workflow
    assert wrapped_runtime_gate is runtime_gate


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
