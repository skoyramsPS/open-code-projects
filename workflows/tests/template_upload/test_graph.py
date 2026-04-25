from __future__ import annotations

import pytest


def test_target_tree_wrapper_points_to_template_upload_graph_module() -> None:
    from comicbook.upload_graph import build_upload_graph as wrapped_build_upload_graph
    from comicbook.upload_graph import run_upload_workflow as wrapped_run_upload_workflow
    from pipelines.workflows.template_upload.graph import build_upload_graph
    from pipelines.workflows.template_upload.graph import run_upload_workflow

    assert wrapped_build_upload_graph is build_upload_graph
    assert wrapped_run_upload_workflow is run_upload_workflow


def test_template_upload_run_module_uses_moved_graph_module(monkeypatch: pytest.MonkeyPatch) -> None:
    from pipelines.workflows.template_upload import graph as graph_module
    from pipelines.workflows.template_upload import run as run_module

    captured: list[tuple[dict[str, object], object]] = []

    def fake_run_upload_workflow(initial_state: dict[str, object], deps: object) -> dict[str, object]:
        captured.append((dict(initial_state), deps))
        return {"import_run_id": "import-run-1", "run_status": "succeeded"}

    monkeypatch.setattr(graph_module, "run_upload_workflow", fake_run_upload_workflow)

    result = run_module.run_upload_workflow({"import_run_id": "import-run-1"}, object())

    assert result == {"import_run_id": "import-run-1", "run_status": "succeeded"}
    assert captured == [({"import_run_id": "import-run-1"}, captured[0][1])]
