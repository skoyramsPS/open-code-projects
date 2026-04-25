"""Legacy compatibility wrapper for :mod:`pipelines.shared.fingerprint`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[2] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.shared.fingerprint import compute_prompt_fingerprint, materialize_rendered_prompts, render_prompt_text

__all__ = [
    "compute_prompt_fingerprint",
    "materialize_rendered_prompts",
    "render_prompt_text",
]
