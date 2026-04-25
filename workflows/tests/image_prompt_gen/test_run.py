from __future__ import annotations

from types import SimpleNamespace

import pytest


def test_target_tree_wrapper_points_to_image_run_entry_points() -> None:
    from comicbook.run import main as wrapped_main
    from comicbook.run import parse_args as wrapped_parse_args
    from comicbook.run import run_batch as wrapped_run_batch
    from comicbook.run import run_once as wrapped_run_once
    from pipelines.workflows.image_prompt_gen.run import main
    from pipelines.workflows.image_prompt_gen.run import parse_args
    from pipelines.workflows.image_prompt_gen.run import run_batch
    from pipelines.workflows.image_prompt_gen.run import run_once

    assert wrapped_main is main
    assert wrapped_parse_args is parse_args
    assert wrapped_run_batch is run_batch
    assert wrapped_run_once is run_once


def test_run_batch_emits_structured_log_events(monkeypatch: pytest.MonkeyPatch) -> None:
    from comicbook.input_file import InputPromptRecord
    from pipelines.workflows.image_prompt_gen import run as run_module

    records = [
        InputPromptRecord(user_prompt="First prompt", run_id="batch-run-1"),
        InputPromptRecord(user_prompt="Second prompt"),
    ]
    events: list[tuple[object, str, dict[str, object]]] = []

    def capture_log_event(logger: object, event: str, **fields: object) -> None:
        events.append((logger, event, dict(fields)))

    def fake_run_once(user_prompt: str, **kwargs: object) -> dict[str, str]:
        run_id = str(kwargs["run_id"])
        if run_id == "generated-run-2":
            raise RuntimeError("router exploded")
        return {"run_id": run_id, "run_status": "succeeded"}

    monkeypatch.setattr(run_module, "log_event", capture_log_event)
    monkeypatch.setattr(run_module, "run_once", fake_run_once)

    summary = run_module.run_batch(
        records,
        input_file="examples/prompts.sample.json",
        deps=SimpleNamespace(uuid_factory=lambda: "generated-run-2"),
    )

    assert summary == {
        "input_file": "examples/prompts.sample.json",
        "total_records": 2,
        "succeeded": 1,
        "partial": 0,
        "dry_run": 0,
        "failed": 1,
        "run_ids": ["batch-run-1", "generated-run-2"],
    }
    assert [event for _, event, _ in events] == [
        "batch_record_started",
        "batch_record_completed",
        "batch_record_started",
        "batch_record_failed",
        "batch_completed",
    ]
    assert all(fields["workflow"] == "image_prompt_gen" for _, _, fields in events)
    assert events[0][2]["run_id"] == "batch-run-1"
    assert events[1][2]["run_status"] == "succeeded"
    assert events[3][2]["run_id"] == "generated-run-2"
    assert events[3][2]["level"] == "ERROR"


def test_main_logs_input_file_validation_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pipelines.workflows.image_prompt_gen import run as run_module

    events: list[tuple[str, dict[str, object]]] = []

    def capture_log_event(logger: object, event: str, **fields: object) -> None:
        events.append((event, dict(fields)))

    def raise_validation_error(path: str) -> list[object]:
        raise run_module.InputFileValidationError(f"{path}: invalid JSON")

    monkeypatch.setattr(run_module, "log_event", capture_log_event)
    monkeypatch.setattr(run_module, "load_input_records", raise_validation_error)

    exit_code = run_module.main(["--input-file", "examples/prompts.sample.json"])

    assert exit_code == 1
    assert "invalid JSON" in capsys.readouterr().err
    assert events == [
        (
            "input_file_validation_failed",
            {
                "workflow": "image_prompt_gen",
                "level": "ERROR",
                "message": "Input file validation failed",
                "input_file": "examples/prompts.sample.json",
                "error_message": "examples/prompts.sample.json: invalid JSON",
            },
        )
    ]
