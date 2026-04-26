from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_ROOT = REPO_ROOT / "workflows" / "pipelines"


def _import_targets(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
        elif isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
    return targets


def _python_files(path: Path) -> list[Path]:
    return [candidate for candidate in path.rglob("*.py") if "__pycache__" not in candidate.parts]


def test_shared_modules_do_not_import_workflow_state_modules() -> None:
    forbidden = {
        "pipelines.workflows.image_prompt_gen.state",
        "pipelines.workflows.template_upload.state",
    }

    offending = [
        path.relative_to(REPO_ROOT)
        for path in _python_files(WORKFLOWS_ROOT / "shared")
        if _import_targets(path).intersection(forbidden)
    ]

    assert offending == []


def test_workflows_do_not_import_each_others_state_modules() -> None:
    image_forbidden = "pipelines.workflows.template_upload.state"
    upload_forbidden = "pipelines.workflows.image_prompt_gen.state"

    image_offending = [
        path.relative_to(REPO_ROOT)
        for path in _python_files(WORKFLOWS_ROOT / "workflows" / "image_prompt_gen")
        if image_forbidden in _import_targets(path)
    ]
    upload_offending = [
        path.relative_to(REPO_ROOT)
        for path in _python_files(WORKFLOWS_ROOT / "workflows" / "template_upload")
        if upload_forbidden in _import_targets(path)
    ]

    assert image_offending == []
    assert upload_offending == []
