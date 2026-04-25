"""Workflow configuration loading.

This module intentionally copies the lightweight `.env` parsing pattern from
`workflows/DoNotChange/hello_azure_openai.py` instead of importing it. The
reference scripts are read-only, and the implementation guide requires the new
workflow package to own its reusable runtime helpers directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator


class ConfigError(ValueError):
    """Raised when workflow configuration is missing or invalid."""


REQUIRED_ENV_VARS: Final[tuple[str, ...]] = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_CHAT_DEPLOYMENT",
    "AZURE_OPENAI_IMAGE_DEPLOYMENT",
)

OPTIONAL_ENV_DEFAULTS: Final[dict[str, str]] = {
    "COMICBOOK_DB_PATH": "./comicbook.sqlite",
    "COMICBOOK_IMAGE_OUTPUT_DIR": "./image_output",
    "COMICBOOK_RUNS_DIR": "./runs",
    "COMICBOOK_LOGS_DIR": "./logs",
    "COMICBOOK_IMPORT_MAX_ROWS_PER_FILE": "1000",
    "COMICBOOK_IMPORT_MAX_FILE_BYTES": "5000000",
    "COMICBOOK_IMPORT_ALLOW_EXTERNAL_PATH": "0",
    "COMICBOOK_IMPORT_BACKFILL_MODEL": "gpt-5.4-mini",
    "COMICBOOK_ROUTER_MODEL_FALLBACK": "gpt-5.4-mini",
    "COMICBOOK_ROUTER_MODEL_ESCALATION": "gpt-5.4",
    "COMICBOOK_ROUTER_PROMPT_VERSION": "ROUTER_SYSTEM_PROMPT_V2",
    "COMICBOOK_ENABLE_ROUTER_PREFLIGHT": "0",
}

ENV_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "AZURE_OPENAI_API_KEY": ("AZURE_API_KEY",),
}


def load_dotenv(dotenv_path: str | Path = ".env") -> dict[str, str]:
    """Load key=value pairs from a `.env` file.

    The parser intentionally stays small and dependency-free because the guide
    calls for env-first loading with a `.env` fallback that mirrors the
    repository's read-only reference scripts.
    """

    path = Path(dotenv_path)
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        values[key] = value

    return values


def _config_value(name: str, dotenv_values: dict[str, str], default: str | None = None) -> str | None:
    from os import getenv

    raw = getenv(name)
    if raw:
        return raw

    for alias in ENV_ALIASES.get(name, ()):  # pragma: no branch - tiny mapping
        alias_value = getenv(alias) or dotenv_values.get(alias)
        if alias_value:
            return alias_value

    return dotenv_values.get(name) or default


def _parse_bool(raw: str | bool) -> bool:
    if isinstance(raw, bool):
        return raw

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Unsupported boolean value: {raw!r}")


class AppConfig(BaseModel):
    """Validated workflow configuration resolved from environment sources."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    azure_openai_endpoint: str
    azure_openai_api_key: SecretStr
    azure_openai_api_version: str
    azure_openai_chat_deployment: str
    azure_openai_image_deployment: str
    comicbook_db_path: Path = Field(default=Path("./comicbook.sqlite"))
    comicbook_image_output_dir: Path = Field(default=Path("./image_output"))
    comicbook_runs_dir: Path = Field(default=Path("./runs"))
    comicbook_logs_dir: Path = Field(default=Path("./logs"))
    comicbook_import_max_rows_per_file: int = 1000
    comicbook_import_max_file_bytes: int = 5_000_000
    comicbook_import_allow_external_path: bool = False
    comicbook_import_backfill_model: str = Field(default="gpt-5.4-mini")
    comicbook_router_model_fallback: str = Field(default="gpt-5.4-mini")
    comicbook_router_model_escalation: str = Field(default="gpt-5.4")
    comicbook_daily_budget_usd: float | None = None
    comicbook_router_prompt_version: str = Field(default="ROUTER_SYSTEM_PROMPT_V2")
    comicbook_enable_router_preflight: bool = False

    @field_validator(
        "azure_openai_endpoint",
        "azure_openai_api_version",
        "azure_openai_chat_deployment",
        "azure_openai_image_deployment",
        "comicbook_import_backfill_model",
        "comicbook_router_model_fallback",
        "comicbook_router_model_escalation",
        "comicbook_router_prompt_version",
        mode="before",
    )
    @classmethod
    def _non_empty_string(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("azure_openai_endpoint", mode="after")
    @classmethod
    def _normalize_endpoint(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("comicbook_enable_router_preflight", "comicbook_import_allow_external_path", mode="before")
    @classmethod
    def _normalize_bool(cls, value: str | bool) -> bool:
        return _parse_bool(value)

    @field_validator("comicbook_import_max_rows_per_file", "comicbook_import_max_file_bytes")
    @classmethod
    def _require_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be greater than zero")
        return value


def load_config(dotenv_path: str | Path = ".env") -> AppConfig:
    """Resolve config with env-first, `.env` fallback semantics."""

    dotenv_values = load_dotenv(dotenv_path)

    missing = [name for name in REQUIRED_ENV_VARS if not _config_value(name, dotenv_values)]
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(f"Missing required configuration values: {joined}")

    raw_values = {
        "azure_openai_endpoint": _config_value("AZURE_OPENAI_ENDPOINT", dotenv_values),
        "azure_openai_api_key": _config_value("AZURE_OPENAI_API_KEY", dotenv_values),
        "azure_openai_api_version": _config_value("AZURE_OPENAI_API_VERSION", dotenv_values),
        "azure_openai_chat_deployment": _config_value("AZURE_OPENAI_CHAT_DEPLOYMENT", dotenv_values),
        "azure_openai_image_deployment": _config_value("AZURE_OPENAI_IMAGE_DEPLOYMENT", dotenv_values),
        "comicbook_db_path": _config_value(
            "COMICBOOK_DB_PATH",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_DB_PATH"],
        ),
        "comicbook_image_output_dir": _config_value(
            "COMICBOOK_IMAGE_OUTPUT_DIR",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_IMAGE_OUTPUT_DIR"],
        ),
        "comicbook_runs_dir": _config_value(
            "COMICBOOK_RUNS_DIR",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_RUNS_DIR"],
        ),
        "comicbook_logs_dir": _config_value(
            "COMICBOOK_LOGS_DIR",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_LOGS_DIR"],
        ),
        "comicbook_import_max_rows_per_file": _config_value(
            "COMICBOOK_IMPORT_MAX_ROWS_PER_FILE",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_IMPORT_MAX_ROWS_PER_FILE"],
        ),
        "comicbook_import_max_file_bytes": _config_value(
            "COMICBOOK_IMPORT_MAX_FILE_BYTES",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_IMPORT_MAX_FILE_BYTES"],
        ),
        "comicbook_import_allow_external_path": _config_value(
            "COMICBOOK_IMPORT_ALLOW_EXTERNAL_PATH",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_IMPORT_ALLOW_EXTERNAL_PATH"],
        ),
        "comicbook_import_backfill_model": _config_value(
            "COMICBOOK_IMPORT_BACKFILL_MODEL",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_IMPORT_BACKFILL_MODEL"],
        ),
        "comicbook_router_model_fallback": _config_value(
            "COMICBOOK_ROUTER_MODEL_FALLBACK",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_ROUTER_MODEL_FALLBACK"],
        ),
        "comicbook_router_model_escalation": _config_value(
            "COMICBOOK_ROUTER_MODEL_ESCALATION",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_ROUTER_MODEL_ESCALATION"],
        ),
        "comicbook_daily_budget_usd": _config_value("COMICBOOK_DAILY_BUDGET_USD", dotenv_values),
        "comicbook_router_prompt_version": _config_value(
            "COMICBOOK_ROUTER_PROMPT_VERSION",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_ROUTER_PROMPT_VERSION"],
        ),
        "comicbook_enable_router_preflight": _config_value(
            "COMICBOOK_ENABLE_ROUTER_PREFLIGHT",
            dotenv_values,
            OPTIONAL_ENV_DEFAULTS["COMICBOOK_ENABLE_ROUTER_PREFLIGHT"],
        ),
    }

    if raw_values["comicbook_daily_budget_usd"] == "":
        raw_values["comicbook_daily_budget_usd"] = None

    try:
        return AppConfig.model_validate(raw_values)
    except ValidationError as exc:  # pragma: no cover - exercised by tests via surface exception
        raise ConfigError(str(exc)) from exc


__all__ = ["AppConfig", "ConfigError", "REQUIRED_ENV_VARS", "load_config", "load_dotenv"]
