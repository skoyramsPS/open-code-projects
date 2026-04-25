"""Git-based helpers for protecting reference paths during the migration."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

DEFAULT_PROTECTED_PATHS: tuple[str, ...] = ("workflows/DoNotChange",)


def resolve_repo_root(start_path: Path) -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip())


def collect_modified_protected_paths(
    repo_root: Path,
    protected_paths: Sequence[str] = DEFAULT_PROTECTED_PATHS,
) -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            *protected_paths,
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line[3:].strip() for line in completed.stdout.splitlines() if line.strip()]


def build_violation_message(modified_paths: Sequence[str], protected_paths: Sequence[str]) -> str:
    scoped_paths = ", ".join(f"`{path}`" for path in protected_paths)
    lines = [
        f"Protected reference files were modified under {scoped_paths}.",
        "Revert these changes before committing:",
    ]
    lines.extend(f"- {path}" for path in modified_paths)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when protected reference files change.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path inside the git repository to inspect.",
    )
    parser.add_argument(
        "--protected-path",
        action="append",
        default=[],
        help="Repository-relative path to protect. May be passed multiple times.",
    )
    args = parser.parse_args(argv)

    protected_paths = tuple(args.protected_path) or DEFAULT_PROTECTED_PATHS

    try:
        repo_root = resolve_repo_root(Path(args.repo_root).resolve())
        modified_paths = collect_modified_protected_paths(repo_root, protected_paths)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        print(f"Unable to inspect repository protections: {details}", file=sys.stderr)
        return 2

    if modified_paths:
        print(build_violation_message(modified_paths, protected_paths), file=sys.stderr)
        return 1

    return 0


__all__ = [
    "DEFAULT_PROTECTED_PATHS",
    "build_violation_message",
    "collect_modified_protected_paths",
    "main",
    "resolve_repo_root",
]
