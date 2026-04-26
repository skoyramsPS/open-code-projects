"""Compatibility wrapper for the legacy ``upload_parse_and_validate`` node."""

from __future__ import annotations

from pipelines.workflows.template_upload.nodes.parse_and_validate import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.parse_and_validate import parse_and_validate as upload_parse_and_validate  # noqa: F401
