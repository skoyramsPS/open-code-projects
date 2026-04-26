"""Compatibility wrapper for the legacy ``upload_resume_filter`` node."""

from __future__ import annotations

from pipelines.workflows.template_upload.nodes.resume_filter import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.resume_filter import resume_filter as upload_resume_filter  # noqa: F401
