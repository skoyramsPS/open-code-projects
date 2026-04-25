"""Compatibility alias for :mod:`pipelines.workflows.image_prompt_gen.prompts.router_prompts`."""

from __future__ import annotations

import sys

from pipelines.workflows.image_prompt_gen.prompts import router_prompts as _router_prompts_module

sys.modules[__name__] = _router_prompts_module
