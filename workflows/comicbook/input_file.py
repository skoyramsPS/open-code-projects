"""Compatibility alias for :mod:`pipelines.workflows.image_prompt_gen.input_file`."""

from __future__ import annotations

import sys

from pipelines.workflows.image_prompt_gen import input_file as _input_file_module

sys.modules[__name__] = _input_file_module
