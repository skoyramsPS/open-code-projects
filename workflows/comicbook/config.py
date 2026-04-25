"""Compatibility wrapper for :mod:`pipelines.shared.config`."""

from pipelines.shared.config import AppConfig, ConfigError, REQUIRED_ENV_VARS, load_config, load_dotenv

__all__ = ["AppConfig", "ConfigError", "REQUIRED_ENV_VARS", "load_config", "load_dotenv"]
