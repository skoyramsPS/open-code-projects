"""Legacy compatibility wrapper for :mod:`pipelines.shared.config`."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[2] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.shared.config import AppConfig, ConfigError, REQUIRED_ENV_VARS, load_config, load_dotenv

__all__ = ["AppConfig", "ConfigError", "REQUIRED_ENV_VARS", "load_config", "load_dotenv"]
