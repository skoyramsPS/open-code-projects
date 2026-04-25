"""Legacy compatibility alias for :mod:`pipelines.workflows.template_upload.nodes.upload_parse_and_validate`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[3] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.workflows.template_upload.nodes import upload_parse_and_validate as _upload_parse_and_validate_module

sys.modules[__name__] = _upload_parse_and_validate_module
