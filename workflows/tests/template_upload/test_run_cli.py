from __future__ import annotations

import importlib
import io
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pytest

from pipelines.shared.db import ComicBookDB
from pipelines.shared.db import RunLockError
from pipelines.shared.deps import Deps
from pipelines.workflows.template_upload.run import main
from pipelines.workflows.template_upload.run import parse_args
from pipelines.workflows.template_upload.run import upload_templates

from .support import db
from .support import make_config


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


def test_parse_args_accepts_positional_source_file() -> None:
    parsed = parse_args(["templates.json", "--dry-run"])

    assert parsed.source_file == "templates.json"
    assert parsed.stdin is False
    assert parsed.dry_run is True


def test_parse_args_accepts_stdin_without_source_file() -> None:
    parsed = parse_args(["--stdin", "--no-backfill"])

    assert parsed.source_file is None
    assert parsed.stdin is True
    assert parsed.no_backfill is True


def test_parse_args_rejects_missing_source(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_args([])

    assert excinfo.value.code == 2
    assert "exactly one source must be provided" in capsys.readouterr().err


def test_parse_args_rejects_both_source_file_and_stdin(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["templates.json", "--stdin"])

    assert excinfo.value.code == 2
    assert "exactly one source must be provided" in capsys.readouterr().err


def test_parse_args_rejects_allow_missing_optional_without_no_backfill(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["templates.json", "--allow-missing-optional"])

    assert excinfo.value.code == 2
    assert "--allow-missing-optional requires --no-backfill" in capsys.readouterr().err


def test_parse_args_accepts_runtime_surface_flags() -> None:
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


def test_upload_templates_is_reexported_and_runs_with_provided_deps(tmp_path: Path, db: ComicBookDB) -> None:
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

    final_state = upload_templates(
        source_file=source_file,
        allow_external_path=True,
        deps=make_deps(tmp_path, db),
    )

    assert final_state["run_status"] == "succeeded"
    assert final_state["row_results"][0]["status"] == "inserted"
    assert db.get_template_by_id("storybook-soft") is not None


def test_package_reexport_is_lazy_until_upload_templates_is_accessed() -> None:
    sys.modules.pop("comicbook", None)
    sys.modules.pop("comicbook.upload_run", None)

    package = importlib.import_module("comicbook")

    assert "comicbook.upload_run" not in sys.modules

    upload_templates_fn = package.upload_templates

    assert callable(upload_templates_fn)
    assert "comicbook.upload_run" in sys.modules


def test_upload_templates_accepts_stdin_text_with_provided_deps(tmp_path: Path, db: ComicBookDB) -> None:
    stdin_text = json.dumps(
        [
            {
                "template_id": "stdin-template",
                "name": "STDIN Template",
                "style_text": "Painterly moonlit linework.",
                "tags": ["moonlit"],
                "summary": "Painterly import from stdin.",
            }
        ]
    )

    final_state = upload_templates(stdin_text=stdin_text, deps=make_deps(tmp_path, db))

    assert final_state["run_status"] == "succeeded"
    assert final_state["row_results"][0]["status"] == "inserted"
    assert db.get_template_by_id("stdin-template") is not None


def test_main_reads_stdin_and_returns_zero_on_partial(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from pipelines.workflows.template_upload import run as run_module

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

    monkeypatch.setattr(run_module, "upload_templates", fake_upload_templates)
    monkeypatch.setattr("sys.stdin", io.StringIO('[{"template_id": "stdin-row"}]'))

    exit_code = main(["--stdin"])

    assert exit_code == 0
    assert captured["source_file"] is None
    assert captured["stdin_text"] == '[{"template_id": "stdin-row"}]'
    assert "import-run-1" in capsys.readouterr().out


def test_main_maps_import_lock_error_to_exit_code_4(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from pipelines.workflows.template_upload import run as run_module

    def fake_upload_templates(**kwargs):  # type: ignore[no-untyped-def]
        raise RunLockError("lock held")

    monkeypatch.setattr(run_module, "upload_templates", fake_upload_templates)

    exit_code = main(["templates.json"])

    assert exit_code == 4
    assert "lock held" in capsys.readouterr().err
