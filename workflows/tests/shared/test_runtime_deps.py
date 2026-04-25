from __future__ import annotations

import logging
from pathlib import Path

import httpx

from pipelines.shared.config import AppConfig
from pipelines.shared.db import ComicBookDB
from pipelines.shared.logging import get_logger


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig.model_validate(
        {
            "azure_openai_endpoint": "https://example.openai.azure.com",
            "azure_openai_api_key": "test-key",
            "azure_openai_api_version": "2025-04-01-preview",
            "azure_openai_chat_deployment": "gpt-5-router",
            "azure_openai_image_deployment": "gpt-image-1.5",
            "comicbook_db_path": tmp_path / "comicbook.sqlite",
            "comicbook_image_output_dir": tmp_path / "image_output",
            "comicbook_runs_dir": tmp_path / "runs",
            "comicbook_logs_dir": tmp_path / "logs",
        }
    )


def test_legacy_wrapper_points_to_shared_runtime_deps_surface() -> None:
    from comicbook.runtime_deps import build_runtime_deps as legacy_build_runtime_deps
    from comicbook.runtime_deps import close_managed_runtime_deps as legacy_close_managed_runtime_deps
    from comicbook.runtime_deps import load_pricing as legacy_load_pricing
    from comicbook.runtime_deps import resolve_runtime_deps as legacy_resolve_runtime_deps
    from pipelines.shared.runtime_deps import build_runtime_deps, close_managed_runtime_deps, load_pricing, resolve_runtime_deps

    assert legacy_load_pricing is load_pricing
    assert legacy_build_runtime_deps is build_runtime_deps
    assert legacy_resolve_runtime_deps is resolve_runtime_deps
    assert legacy_close_managed_runtime_deps is close_managed_runtime_deps


def test_target_tree_package_root_still_reexports_upload_templates() -> None:
    from comicbook import upload_templates as package_export
    from comicbook.upload_run import upload_templates as legacy_upload_templates

    assert package_export is legacy_upload_templates
    assert callable(package_export)


def test_load_pricing_reads_explicit_path(tmp_path: Path) -> None:
    from pipelines.shared.runtime_deps import load_pricing

    pricing_path = tmp_path / "pricing.json"
    pricing_path.write_text('{"image_models":{"gpt-image-1.5":{"usd":0.02}}}', encoding="utf-8")

    assert load_pricing(pricing_path) == {"image_models": {"gpt-image-1.5": {"usd": 0.02}}}


def test_load_pricing_uses_repo_default_when_no_override_is_provided() -> None:
    from pipelines.shared.runtime_deps import load_pricing

    pricing = load_pricing()

    assert pricing == {"router_models": {}, "image_models": {}}


def test_build_runtime_deps_creates_managed_resources_and_directories(tmp_path: Path) -> None:
    from pipelines.shared.runtime_deps import build_runtime_deps, close_managed_runtime_deps

    config = make_config(tmp_path)
    pricing_path = tmp_path / "pricing.json"
    pricing_path.write_text('{"image_models":{"gpt-image-1.5":{"usd":0.02}}}', encoding="utf-8")

    deps, db, http_client = build_runtime_deps(config, pricing_path=pricing_path)
    try:
        assert deps.db is db
        assert deps.http_client is http_client
        assert isinstance(db, ComicBookDB)
        assert isinstance(http_client, httpx.Client)
        assert deps.output_dir == config.comicbook_image_output_dir
        assert deps.runs_dir == config.comicbook_runs_dir
        assert deps.logs_dir == config.comicbook_logs_dir
        assert deps.pricing == {"image_models": {"gpt-image-1.5": {"usd": 0.02}}}
        assert deps.logger is get_logger("pipelines.shared.runtime_deps")
        assert deps.logger.name == "pipelines.shared.runtime_deps"
        assert deps.pid_provider() > 0
        assert isinstance(deps.hostname_provider(), str)
        assert config.comicbook_image_output_dir.is_dir()
        assert config.comicbook_runs_dir.is_dir()
        assert config.comicbook_logs_dir.is_dir()
    finally:
        close_managed_runtime_deps(db, http_client)


def test_resolve_runtime_deps_reuses_caller_supplied_deps(tmp_path: Path) -> None:
    from pipelines.shared.runtime_deps import resolve_runtime_deps

    config = make_config(tmp_path)
    deps = type("DepsStub", (), {"config": config, "db": object(), "http_client": object(), "logger": logging.getLogger("provided")})()

    resolved, managed_db, managed_http_client = resolve_runtime_deps(deps, dotenv_path=tmp_path / ".env")

    assert resolved is deps
    assert managed_db is None
    assert managed_http_client is None


def test_resolve_runtime_deps_builds_managed_resources_when_missing(tmp_path: Path, monkeypatch) -> None:
    from pipelines.shared import runtime_deps as module

    config = make_config(tmp_path)
    expected = (object(), object(), object())

    seen: dict[str, object] = {}

    def fake_load_config(dotenv_path: str | Path) -> AppConfig:
        seen["dotenv_path"] = Path(dotenv_path)
        return config

    def fake_build_runtime_deps(runtime_config: AppConfig, *, pricing_path: Path | None = None):
        seen["config"] = runtime_config
        seen["pricing_path"] = pricing_path
        return expected

    monkeypatch.setattr(module, "load_config", fake_load_config)
    monkeypatch.setattr(module, "build_runtime_deps", fake_build_runtime_deps)

    resolved = module.resolve_runtime_deps(None, dotenv_path=tmp_path / ".env")

    assert resolved == expected
    assert seen == {
        "dotenv_path": tmp_path / ".env",
        "config": config,
        "pricing_path": None,
    }


def test_close_managed_runtime_deps_closes_present_resources() -> None:
    from pipelines.shared.runtime_deps import close_managed_runtime_deps

    events: list[str] = []

    class DBStub:
        def close(self) -> None:
            events.append("db")

    class ClientStub:
        def close(self) -> None:
            events.append("client")

    close_managed_runtime_deps(DBStub(), ClientStub())
    close_managed_runtime_deps(None, None)

    assert events == ["client", "db"]
