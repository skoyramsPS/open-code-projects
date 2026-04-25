from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from comicbook.repo_protection import DEFAULT_PROTECTED_PATHS as LegacyProtectedPaths
from comicbook.repo_protection import collect_modified_protected_paths as legacy_collect_modified_protected_paths
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

    protected_file = repo_root / "ComicBook" / "DoNotChange" / "hello_azure_openai.py"
    protected_file.parent.mkdir(parents=True, exist_ok=True)
    protected_file.write_text("print('hello')\n", encoding="utf-8")

    run_git(repo_root, "init")
    run_git(repo_root, "add", ".")
    run_git(repo_root, "commit", "-m", "baseline")
    return repo_root


def test_target_and_compatibility_modules_share_repo_protection_surface() -> None:
    assert LegacyProtectedPaths == DEFAULT_PROTECTED_PATHS
    assert legacy_collect_modified_protected_paths is collect_modified_protected_paths


def test_collect_modified_protected_paths_returns_empty_for_clean_repo(temp_repo: Path) -> None:
    assert collect_modified_protected_paths(temp_repo) == []


def test_collect_modified_protected_paths_detects_staged_changes(temp_repo: Path) -> None:
    protected_file = temp_repo / "ComicBook" / "DoNotChange" / "hello_azure_openai.py"
    protected_file.write_text("print('staged change')\n", encoding="utf-8")
    run_git(temp_repo, "add", "ComicBook/DoNotChange/hello_azure_openai.py")

    assert collect_modified_protected_paths(temp_repo) == ["ComicBook/DoNotChange/hello_azure_openai.py"]


def test_build_violation_message_lists_scoped_paths() -> None:
    message = build_violation_message(
        ["ComicBook/DoNotChange/hello_azure_openai.py"],
        DEFAULT_PROTECTED_PATHS,
    )

    assert "`ComicBook/DoNotChange`" in message
    assert "- ComicBook/DoNotChange/hello_azure_openai.py" in message


def test_legacy_cli_script_still_fails_when_protected_file_changes(temp_repo: Path) -> None:
    protected_file = temp_repo / "ComicBook" / "DoNotChange" / "hello_azure_openai.py"
    protected_file.write_text("print('changed')\n", encoding="utf-8")

    script_path = Path(__file__).resolve().parents[3] / "ComicBook" / "scripts" / "check_do_not_change.py"
    result = subprocess.run(
        [sys.executable, str(script_path.resolve()), "--repo-root", str(temp_repo)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "ComicBook/DoNotChange/hello_azure_openai.py" in result.stderr
