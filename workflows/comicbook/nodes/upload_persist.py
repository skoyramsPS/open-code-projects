"""Compatibility wrapper for the legacy ``upload_persist`` node."""

from __future__ import annotations

from pipelines.workflows.template_upload.nodes.persist import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.persist import persist as upload_persist  # noqa: F401
