"""Compatibility alias for :mod:`pipelines.workflows.image_prompt_gen.run`."""

from __future__ import annotations

import sys

from pipelines.workflows.image_prompt_gen import run as _run_module

sys.modules[__name__] = _run_module
