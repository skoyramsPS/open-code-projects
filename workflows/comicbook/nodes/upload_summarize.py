"""Compatibility wrapper for the legacy ``upload_summarize`` node."""

from __future__ import annotations

from pipelines.workflows.template_upload.nodes.summarize import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.summarize import summarize as upload_summarize  # noqa: F401
