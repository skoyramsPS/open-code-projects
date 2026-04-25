"""Compatibility alias for :mod:`pipelines.workflows.image_prompt_gen.adapters.image_client`."""

from __future__ import annotations

import sys

from pipelines.workflows.image_prompt_gen.adapters import image_client as _image_client_module

sys.modules[__name__] = _image_client_module
