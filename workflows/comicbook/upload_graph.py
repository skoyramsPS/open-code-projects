"""Compatibility alias for :mod:`pipelines.workflows.template_upload.graph`."""

from __future__ import annotations

import sys

from pipelines.workflows.template_upload import graph as _graph_module

sys.modules[__name__] = _graph_module
