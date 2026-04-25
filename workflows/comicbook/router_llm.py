"""Compatibility alias for :mod:`pipelines.workflows.image_prompt_gen.adapters.router_llm`."""

from __future__ import annotations

import sys

from pipelines.workflows.image_prompt_gen.adapters import router_llm as _router_llm_module

sys.modules[__name__] = _router_llm_module
