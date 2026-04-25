from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipelines.shared.db import RunLockError


def test_target_tree_wrapper_points_to_template_upload_entry_points() -> None:
    from comicbook.upload_run import main as wrapped_main
    from comicbook.upload_run import parse_args as wrapped_parse_args
    from comicbook.upload_run import upload_templates as wrapped_upload_templates
    from pipelines.workflows.template_upload.run import main
    from pipelines.workflows.template_upload.run import parse_args
    from pipelines.workflows.template_upload.run import upload_templates

    assert wrapped_main is main
    assert wrapped_parse_args is parse_args
    assert wrapped_upload_templates is upload_templates


def test_upload_templates_emits_structured_log_events(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from pipelines.workflows.template_upload import run as run_module

    source_file = tmp_path / "templates.json"
    source_file.write_text(json.dumps([]), encoding="utf-8")

    events: list[tuple[str, dict[str, object]]] = []
    lock_calls: list[dict[str, object]] = []

    def capture_log_event(logger: object, event: str, **fields: object) -> None:
        events.append((event, dict(fields)))

    def acquire_import_lock(**kwargs: object) -> None:
        lock_calls.append(dict(kwargs))

    monkeypatch.setattr(run_module, "log_event", capture_log_event)
    monkeypatch.setattr(
        run_module,
        "run_upload_workflow",
        lambda state, deps: {**state, "run_status": "succeeded", "report_path": "runs/import-1/report.md"},
    )

    deps = SimpleNamespace(
        uuid_factory=lambda: "import-run-1",
        clock=lambda: datetime(2026, 4, 25, 14, 0, 0),
        db=SimpleNamespace(
            acquire_import_lock=acquire_import_lock,
            get_import_run=lambda import_run_id: None,
            finalize_import_run=lambda **kwargs: None,
        ),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        config=SimpleNamespace(comicbook_import_allow_external_path=False),
    )

    final_state = run_module.upload_templates(source_file=source_file, allow_external_path=True, deps=deps)

    assert final_state["run_status"] == "succeeded"
    assert lock_calls == [
        {
            "import_run_id": "import-run-1",
            "source_file_path": str(source_file.resolve()),
            "source_file_hash": events[0][1]["source_file_hash"],
            "started_at": "2026-04-25T14:00:00Z",
            "dry_run": False,
            "pid": 123,
            "host": "host-a",
            "pid_is_alive": lock_calls[0]["pid_is_alive"],
        }
    ]
    assert [event for event, _ in events] == ["import_run_started", "import_run_completed"]
    assert events[0][1]["workflow"] == "template_upload"
    assert events[0][1]["run_id"] == "import-run-1"
    assert events[1][1]["run_status"] == "succeeded"


def test_main_logs_run_lock_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pipelines.workflows.template_upload import run as run_module

    events: list[tuple[str, dict[str, object]]] = []

    def capture_log_event(logger: object, event: str, **fields: object) -> None:
        events.append((event, dict(fields)))

    def raise_lock_error(**kwargs: object) -> dict[str, object]:
        raise RunLockError("lock held")

    monkeypatch.setattr(run_module, "log_event", capture_log_event)
    monkeypatch.setattr(run_module, "upload_templates", raise_lock_error)

    exit_code = run_module.main(["templates.json"])

    assert exit_code == 4
    assert "lock held" in capsys.readouterr().err
    assert events == [
        (
            "upload_cli_failed_lock",
            {
                "workflow": "template_upload",
                "level": "ERROR",
                "message": "Template upload lock acquisition failed",
                "error_message": "lock held",
            },
        )
    ]
