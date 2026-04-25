"""Compatibility wrapper for the legacy input-file helpers."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ComicBook.comicbook.input_file import InputFileValidationError, InputPromptRecord, load_input_records

__all__ = ["InputFileValidationError", "InputPromptRecord", "load_input_records"]
