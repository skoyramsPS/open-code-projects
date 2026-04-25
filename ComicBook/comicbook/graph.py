"""Legacy compatibility alias for :mod:`pipelines.workflows.image_prompt_gen.graph`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[2] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.workflows.image_prompt_gen import graph as _graph_module

sys.modules[__name__] = _graph_module
