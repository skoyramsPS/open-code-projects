"""Legacy compatibility alias for :mod:`pipelines.workflows.image_prompt_gen.adapters.image_client`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[2] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.workflows.image_prompt_gen.adapters import image_client as _image_client_module

sys.modules[__name__] = _image_client_module
