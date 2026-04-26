"""Compatibility wrapper for the legacy ``upload_load_file`` node."""

from __future__ import annotations

from pipelines.workflows.template_upload.nodes.load_file import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.load_file import load_file as upload_load_file  # noqa: F401
