from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from comicbook.config import AppConfig
from comicbook.db import ComicBookDB, RunLockError
from comicbook.deps import Deps


def test_parse_args_accepts_positional_source_file() -> None:
    from comicbook.upload_run import parse_args

    parsed = parse_args(["templates.json", "--dry-run"])

    assert parsed.source_file == "templates.json"
    assert parsed.stdin is False
    assert parsed.dry_run is True


def test_parse_args_accepts_stdin_without_source_file() -> None:
    from comicbook.upload_run import parse_args

    parsed = parse_args(["--stdin", "--no-backfill"])

    assert parsed.source_file is None
    assert parsed.stdin is True
    assert parsed.no_backfill is True


def test_parse_args_rejects_missing_source(capsys: pytest.CaptureFixture[str]) -> None:
    from comicbook.upload_run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args([])

    assert excinfo.value.code == 2
    assert "exactly one source must be provided" in capsys.readouterr().err


def test_parse_args_rejects_both_source_file_and_stdin(capsys: pytest.CaptureFixture[str]) -> None:
    from comicbook.upload_run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args(["templates.json", "--stdin"])

    assert excinfo.value.code == 2
    assert "exactly one source must be provided" in capsys.readouterr().err


def test_parse_args_rejects_allow_missing_optional_without_no_backfill(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from comicbook.upload_run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args(["templates.json", "--allow-missing-optional"])

    assert excinfo.value.code == 2
    assert "--allow-missing-optional requires --no-backfill" in capsys.readouterr().err


def test_parse_args_accepts_runtime_surface_flags() -> None:
    from comicbook.upload_run import parse_args

    parsed = parse_args(
        [
            "templates.json",
            "--budget-usd",
            "1.5",
            "--redact-style-text-in-logs",
            "--allow-external-path",
        ]
    )

    assert parsed.source_file == "templates.json"
    assert parsed.budget_usd == pytest.approx(1.5)
    assert parsed.redact_style_text_in_logs is True
    assert parsed.allow_external_path is True


@pytest.fixture
def db(tmp_path: Path) -> ComicBookDB:
    database = ComicBookDB.connect(tmp_path / "comicbook.sqlite")
    try:
        yield database
    finally:
        database.close()


def make_config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "azure_openai_endpoint": "https://example.openai.azure.com",
            "azure_openai_api_key": "test-key",
            "azure_openai_api_version": "2025-04-01-preview",
            "azure_openai_chat_deployment": "gpt-5-router",
            "azure_openai_image_deployment": "gpt-image-1.5",
        }
    )


def make_deps(tmp_path: Path, db: ComicBookDB) -> Deps:
    return Deps(
        config=make_config(),
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "generated-import-run-id",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"router_models": {}},
        logger=logging.getLogger("test-upload-run"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
    )


def test_upload_templates_is_reexported_and_runs_with_provided_deps(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook import upload_templates

    payload = [
        {
            "template_id": "storybook-soft",
            "name": "Storybook Soft",
            "style_text": "Soft painterly linework.",
            "tags": ["storybook"],
            "summary": "Warm storybook lighting.",
        }
    ]
    source_file = tmp_path / "templates.json"
    source_file.write_text(json.dumps(payload), encoding="utf-8")

    final_state = upload_templates(source_file=source_file, deps=make_deps(tmp_path, db))

    assert final_state["run_status"] == "succeeded"
    assert final_state["row_results"][0]["status"] == "inserted"
    assert db.get_template_by_id("storybook-soft") is not None


def test_main_reads_stdin_and_returns_zero_on_partial(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from comicbook import upload_run

    captured: dict[str, object] = {}

    def fake_upload_templates(*, source_file=None, stdin_text=None, **kwargs):  # type: ignore[no-untyped-def]
        captured["source_file"] = source_file
        captured["stdin_text"] = stdin_text
        return {
            "import_run_id": "import-run-1",
            "run_status": "partial",
            "report_path": "runs/import-run-1/import_report.md",
            "row_results": [{"status": "failed"}],
        }

    monkeypatch.setattr(upload_run, "upload_templates", fake_upload_templates)
    monkeypatch.setattr("sys.stdin", io.StringIO("[{\"template_id\": \"stdin-row\"}]"))

    exit_code = upload_run.main(["--stdin"])

    assert exit_code == 0
    assert captured["source_file"] is None
    assert captured["stdin_text"] == "[{\"template_id\": \"stdin-row\"}]"
    assert "import-run-1" in capsys.readouterr().out


def test_main_maps_import_lock_error_to_exit_code_4(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from comicbook import upload_run

    def fake_upload_templates(**kwargs):  # type: ignore[no-untyped-def]
        raise RunLockError("lock held")

    monkeypatch.setattr(upload_run, "upload_templates", fake_upload_templates)

    exit_code = upload_run.main(["templates.json"])

    assert exit_code == 4
    assert "lock held" in capsys.readouterr().err
