"""Legacy compatibility wrapper for :mod:`pipelines.workflows.template_upload.nodes.persist`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[3] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.workflows.template_upload.nodes.persist import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.persist import persist as upload_persist  # noqa: F401
