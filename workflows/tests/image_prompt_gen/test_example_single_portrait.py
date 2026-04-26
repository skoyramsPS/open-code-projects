from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType

from pipelines.shared.db import ComicBookDB

from .support import FakeImageTransport
from .support import FakeRouterTransport
from .support import db
from .support import make_deps
from .support import make_image_response
from .support import make_router_response


def load_moved_example_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "workflows" / "examples" / "single_portrait_graph.py"
    spec = importlib.util.spec_from_file_location("tg2_example_single_portrait", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_moved_single_portrait_example_runs_from_target_tree_root(tmp_path: Path, db: ComicBookDB) -> None:
    example_module = load_moved_example_module()

    router_transport = FakeRouterTransport(
        responses=[make_router_response("Hero portrait in dramatic rim light.")]
    )
    image_transport = FakeImageTransport(responses=[make_image_response(b"portrait-image")])

    final_state = example_module.run_single_portrait_workflow(
        {
            "run_id": "example-run",
            "user_prompt": "Create a hero portrait.",
            "exact_image_count": 4,
        },
        make_deps(tmp_path, db, router_transport, image_transport, logger_name="test-example-single-portrait"),
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


def test_target_tree_shared_modules_do_not_import_workflow_entry_modules() -> None:
    shared_root = Path(__file__).resolve().parents[2] / "pipelines" / "shared"
    offenders: list[str] = []
    forbidden_imports = {
        "pipelines.workflows.image_prompt_gen.graph",
        "pipelines.workflows.image_prompt_gen.run",
        "pipelines.workflows.template_upload.graph",
        "pipelines.workflows.template_upload.run",
    }

    for path in sorted(shared_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_imports:
                        offenders.append(f"{path.relative_to(shared_root.parent.parent)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module in forbidden_imports:
                offenders.append(f"{path.relative_to(shared_root.parent.parent)} imports from {node.module}")

    assert offenders == []
