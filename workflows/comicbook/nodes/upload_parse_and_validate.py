"""Compatibility alias for the legacy ``upload_parse_and_validate`` node."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ComicBook.comicbook.nodes import upload_parse_and_validate as _legacy_module

sys.modules[__name__] = _legacy_module
