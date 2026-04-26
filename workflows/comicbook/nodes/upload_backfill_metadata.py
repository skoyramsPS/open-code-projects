"""Compatibility wrapper for the legacy ``upload_backfill_metadata`` node."""

from __future__ import annotations

from pipelines.workflows.template_upload.nodes.backfill_metadata import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.backfill_metadata import backfill_metadata as upload_backfill_metadata  # noqa: F401
