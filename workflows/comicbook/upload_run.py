"""Compatibility alias for :mod:`pipelines.workflows.template_upload.run`."""

from __future__ import annotations

import sys

from pipelines.workflows.template_upload import run as _run_module

sys.modules[__name__] = _run_module
