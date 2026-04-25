"""Compatibility wrapper for :mod:`pipelines.shared.repo_protection`."""

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
