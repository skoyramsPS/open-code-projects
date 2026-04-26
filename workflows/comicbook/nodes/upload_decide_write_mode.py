"""Compatibility wrapper for the legacy ``upload_decide_write_mode`` node."""

from __future__ import annotations

from pipelines.workflows.template_upload.nodes.decide_write_mode import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.decide_write_mode import decide_write_mode as upload_decide_write_mode  # noqa: F401
