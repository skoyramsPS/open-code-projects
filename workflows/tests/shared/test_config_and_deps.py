from __future__ import annotations

import logging
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path

import pytest

from pipelines.shared.config import AppConfig, ConfigError, load_config
from pipelines.shared.deps import Deps


ALL_ENV_VARS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_API_KEY",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_CHAT_DEPLOYMENT",
    "AZURE_OPENAI_IMAGE_DEPLOYMENT",
    "COMICBOOK_DB_PATH",
    "COMICBOOK_IMAGE_OUTPUT_DIR",
    "COMICBOOK_RUNS_DIR",
    "COMICBOOK_LOGS_DIR",
    "COMICBOOK_IMPORT_MAX_ROWS_PER_FILE",
    "COMICBOOK_IMPORT_MAX_FILE_BYTES",
    "COMICBOOK_IMPORT_ALLOW_EXTERNAL_PATH",
    "COMICBOOK_IMPORT_BACKFILL_MODEL",
    "COMICBOOK_ROUTER_MODEL_FALLBACK",
    "COMICBOOK_ROUTER_MODEL_ESCALATION",
    "COMICBOOK_DAILY_BUDGET_USD",
    "COMICBOOK_ROUTER_PROMPT_VERSION",
    "COMICBOOK_ENABLE_ROUTER_PREFLIGHT",
)


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ALL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_load_config_reads_dotenv_and_defaults_from_target_tree(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com/",
                "AZURE_OPENAI_API_KEY=test-key",
                "AZURE_OPENAI_API_VERSION=2025-04-01-preview",
                "AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-router",
                "AZURE_OPENAI_IMAGE_DEPLOYMENT=gpt-image-1.5",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(dotenv_path=dotenv_path)

    assert isinstance(config, AppConfig)
    assert config.azure_openai_endpoint == "https://example.openai.azure.com"
    assert config.azure_openai_api_key.get_secret_value() == "test-key"
    assert config.comicbook_db_path == Path("./comicbook.sqlite")
    assert config.comicbook_runs_dir == Path("./runs")


def test_environment_overrides_dotenv_in_shared_config_loader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "AZURE_OPENAI_ENDPOINT=https://from-dotenv.example.com",
                "AZURE_OPENAI_API_KEY=dotenv-key",
                "AZURE_OPENAI_API_VERSION=2025-04-01-preview",
                "AZURE_OPENAI_CHAT_DEPLOYMENT=dotenv-router",
                "AZURE_OPENAI_IMAGE_DEPLOYMENT=dotenv-image",
                "COMICBOOK_DB_PATH=./from-dotenv.sqlite",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "env-key")
    monkeypatch.setenv("COMICBOOK_DB_PATH", "./from-env.sqlite")

    config = load_config(dotenv_path=dotenv_path)

    assert config.azure_openai_api_key.get_secret_value() == "env-key"
    assert config.comicbook_db_path == Path("./from-env.sqlite")


def test_deps_remains_frozen_through_shared_module() -> None:
    config = AppConfig.model_validate(
        {
            "azure_openai_endpoint": "https://example.openai.azure.com",
            "azure_openai_api_key": "test-key",
            "azure_openai_api_version": "2025-04-01-preview",
            "azure_openai_chat_deployment": "gpt-5-router",
            "azure_openai_image_deployment": "gpt-image-1.5",
        }
    )

    deps = Deps(
        config=config,
        db=object(),
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "run-1",
        output_dir=Path("image_output"),
        runs_dir=Path("runs"),
        logs_dir=Path("logs"),
        pricing={"image": {}},
        logger=logging.getLogger("test"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "localhost",
    )

    with pytest.raises(FrozenInstanceError):
        deps.output_dir = Path("other")
