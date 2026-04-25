"""Legacy compatibility wrapper for :mod:`pipelines.shared.repo_protection`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[2] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.shared.repo_protection import (
    DEFAULT_PROTECTED_PATHS,
    build_violation_message,
    collect_modified_protected_paths,
    main,
    resolve_repo_root,
)

__all__ = [
    "DEFAULT_PROTECTED_PATHS",
    "build_violation_message",
    "collect_modified_protected_paths",
    "main",
    "resolve_repo_root",
]


if __name__ == "__main__":
    raise SystemExit(main())
