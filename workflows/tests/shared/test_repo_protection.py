from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from pipelines.shared.repo_protection import DEFAULT_PROTECTED_PATHS, build_violation_message, collect_modified_protected_paths


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    protected_file = repo_root / "workflows" / "DoNotChange" / "hello_azure_openai.py"
    protected_file.parent.mkdir(parents=True, exist_ok=True)
    protected_file.write_text("print('hello')\n", encoding="utf-8")

    run_git(repo_root, "init")
    run_git(repo_root, "add", ".")
    run_git(repo_root, "commit", "-m", "baseline")
    return repo_root


def test_collect_modified_protected_paths_returns_empty_for_clean_repo(temp_repo: Path) -> None:
    assert collect_modified_protected_paths(temp_repo) == []


def test_collect_modified_protected_paths_detects_staged_changes(temp_repo: Path) -> None:
    protected_file = temp_repo / "workflows" / "DoNotChange" / "hello_azure_openai.py"
    protected_file.write_text("print('staged change')\n", encoding="utf-8")
    run_git(temp_repo, "add", "workflows/DoNotChange/hello_azure_openai.py")

    assert collect_modified_protected_paths(temp_repo) == ["workflows/DoNotChange/hello_azure_openai.py"]


def test_build_violation_message_lists_scoped_paths() -> None:
    message = build_violation_message(
        ["workflows/DoNotChange/hello_azure_openai.py"],
        DEFAULT_PROTECTED_PATHS,
    )

    assert "`workflows/DoNotChange`" in message
    assert "- workflows/DoNotChange/hello_azure_openai.py" in message


def test_repo_protection_module_cli_fails_when_protected_file_changes(temp_repo: Path) -> None:
    protected_file = temp_repo / "workflows" / "DoNotChange" / "hello_azure_openai.py"
    protected_file.write_text("print('changed')\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "pipelines.shared.repo_protection", "--repo-root", str(temp_repo)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "workflows/DoNotChange/hello_azure_openai.py" in result.stderr
