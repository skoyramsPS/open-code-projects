"""Compatibility alias for the legacy ``upload_persist`` node."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ComicBook.comicbook.nodes import upload_persist as _legacy_module

sys.modules[__name__] = _legacy_module
