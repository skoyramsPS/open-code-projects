"""Compatibility alias for :mod:`pipelines.workflows.image_prompt_gen.graph`."""

from __future__ import annotations

import sys

from pipelines.workflows.image_prompt_gen import graph as _graph_module

sys.modules[__name__] = _graph_module
