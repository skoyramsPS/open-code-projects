"""Legacy compatibility alias for :mod:`pipelines.workflows.template_upload.nodes.upload_decide_write_mode`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[3] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.workflows.template_upload.nodes import upload_decide_write_mode as _upload_decide_write_mode_module

sys.modules[__name__] = _upload_decide_write_mode_module
