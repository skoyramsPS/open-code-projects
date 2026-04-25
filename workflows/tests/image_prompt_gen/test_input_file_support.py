from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_parse_args_accepts_input_file_without_prompt() -> None:
    from pipelines.workflows.image_prompt_gen.run import parse_args

    parsed = parse_args(["--input-file", "examples/prompts.sample.json", "--dry-run"])

    assert parsed.user_prompt is None
    assert parsed.input_file == "examples/prompts.sample.json"
    assert parsed.dry_run is True


def test_parse_args_rejects_missing_prompt_source(capsys: pytest.CaptureFixture[str]) -> None:
    from pipelines.workflows.image_prompt_gen.run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args([])

    assert excinfo.value.code == 2
    assert "exactly one prompt source" in capsys.readouterr().err


def test_parse_args_rejects_both_prompt_sources(capsys: pytest.CaptureFixture[str]) -> None:
    from pipelines.workflows.image_prompt_gen.run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args(["single prompt", "--input-file", "examples/prompts.sample.json"])

    assert excinfo.value.code == 2
    assert "exactly one prompt source" in capsys.readouterr().err


def test_parse_args_rejects_run_id_with_input_file(capsys: pytest.CaptureFixture[str]) -> None:
    from pipelines.workflows.image_prompt_gen.run import parse_args

    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--input-file", "examples/prompts.sample.json", "--run-id", "shared-run"])

    assert excinfo.value.code == 2
    assert "--run-id cannot be used with --input-file" in capsys.readouterr().err


def test_load_input_records_parses_json_in_order_and_trims_values(tmp_path: Path) -> None:
    from pipelines.workflows.image_prompt_gen.input_file import load_input_records

    path = tmp_path / "prompts.json"
    path.write_text(
        json.dumps(
            [
                {"user_prompt": "  First prompt  "},
                {"run_id": "  run-2  ", "user_prompt": "  Second prompt  "},
            ]
        ),
        encoding="utf-8",
    )

    records = load_input_records(path)

    assert [record.user_prompt for record in records] == ["First prompt", "Second prompt"]
    assert [record.run_id for record in records] == [None, "run-2"]


def test_load_input_records_rejects_json_top_level_non_list(tmp_path: Path) -> None:
    from pipelines.workflows.image_prompt_gen.input_file import InputFileValidationError, load_input_records

    path = tmp_path / "prompts.json"
    path.write_text(json.dumps({"user_prompt": "Not a list"}), encoding="utf-8")

    with pytest.raises(InputFileValidationError, match="top-level JSON value must be a list"):
        load_input_records(path)


def test_load_input_records_rejects_json_unknown_field(tmp_path: Path) -> None:
    from pipelines.workflows.image_prompt_gen.input_file import InputFileValidationError, load_input_records

    path = tmp_path / "prompts.json"
    path.write_text(
        json.dumps([{"user_prompt": "Known prompt", "panels": 2}]),
        encoding="utf-8",
    )

    with pytest.raises(InputFileValidationError, match="unsupported field"):
        load_input_records(path)


def test_load_input_records_rejects_json_duplicate_run_ids(tmp_path: Path) -> None:
    from pipelines.workflows.image_prompt_gen.input_file import InputFileValidationError, load_input_records

    path = tmp_path / "prompts.json"
    path.write_text(
        json.dumps(
            [
                {"run_id": "repeat-run", "user_prompt": "First prompt"},
                {"run_id": "repeat-run", "user_prompt": "Second prompt"},
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(InputFileValidationError, match="duplicate run_id"):
        load_input_records(path)


def test_load_input_records_parses_csv_in_order(tmp_path: Path) -> None:
    from pipelines.workflows.image_prompt_gen.input_file import load_input_records

    path = tmp_path / "prompts.csv"
    path.write_text(
        "run_id,user_prompt\n"
        "csv-run-1,  First prompt  \n"
        "csv-run-2,Second prompt\n",
        encoding="utf-8",
    )

    records = load_input_records(path)

    assert [record.run_id for record in records] == ["csv-run-1", "csv-run-2"]
    assert [record.user_prompt for record in records] == ["First prompt", "Second prompt"]


def test_load_input_records_rejects_csv_missing_user_prompt_column(tmp_path: Path) -> None:
    from pipelines.workflows.image_prompt_gen.input_file import InputFileValidationError, load_input_records

    path = tmp_path / "prompts.csv"
    path.write_text("run_id\nmissing-prompt\n", encoding="utf-8")

    with pytest.raises(InputFileValidationError, match="user_prompt"):
        load_input_records(path)


def test_load_input_records_rejects_csv_blank_prompt(tmp_path: Path) -> None:
    from pipelines.workflows.image_prompt_gen.input_file import InputFileValidationError, load_input_records

    path = tmp_path / "prompts.csv"
    path.write_text("user_prompt\n   \n", encoding="utf-8")

    with pytest.raises(InputFileValidationError, match="user_prompt must not be blank"):
        load_input_records(path)


def test_load_input_records_rejects_csv_extra_column(tmp_path: Path) -> None:
    from pipelines.workflows.image_prompt_gen.input_file import InputFileValidationError, load_input_records

    path = tmp_path / "prompts.csv"
    path.write_text("user_prompt,panels\nPrompt text,2\n", encoding="utf-8")

    with pytest.raises(InputFileValidationError, match="unsupported column"):
        load_input_records(path)


def test_run_batch_executes_records_in_order_and_forwards_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    from pipelines.workflows.image_prompt_gen import run as run_module
    from pipelines.workflows.image_prompt_gen.input_file import InputPromptRecord

    records = [
        InputPromptRecord(user_prompt="First prompt", run_id="batch-run-1"),
        InputPromptRecord(user_prompt="Second prompt"),
    ]
    generated_ids = iter(["generated-run-2"])
    deps = SimpleNamespace(
        uuid_factory=lambda: next(generated_ids),
        logger=logging.getLogger("test-input-file-support"),
    )
    calls: list[dict[str, object]] = []

    def fake_run_once(user_prompt: str, **kwargs: object) -> dict[str, str]:
        calls.append({"user_prompt": user_prompt, **kwargs})
        return {"run_id": str(kwargs["run_id"]), "run_status": "dry_run"}

    monkeypatch.setattr(run_module, "run_once", fake_run_once)

    summary = run_module.run_batch(
        records,
        input_file="examples/prompts.sample.json",
        dry_run=True,
        force=True,
        panels=2,
        budget_usd=1.25,
        redact_prompts=True,
        deps=deps,
    )

    assert [call["user_prompt"] for call in calls] == ["First prompt", "Second prompt"]
    assert [call["run_id"] for call in calls] == ["batch-run-1", "generated-run-2"]
    assert all(call["dry_run"] is True for call in calls)
    assert all(call["force"] is True for call in calls)
    assert all(call["panels"] == 2 for call in calls)
    assert all(call["budget_usd"] == pytest.approx(1.25) for call in calls)
    assert all(call["redact_prompts"] is True for call in calls)
    assert summary == {
        "input_file": "examples/prompts.sample.json",
        "total_records": 2,
        "succeeded": 0,
        "partial": 0,
        "dry_run": 2,
        "failed": 0,
        "run_ids": ["batch-run-1", "generated-run-2"],
    }


def test_run_batch_continues_after_runtime_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from pipelines.workflows.image_prompt_gen import run as run_module
    from pipelines.workflows.image_prompt_gen.input_file import InputPromptRecord

    records = [
        InputPromptRecord(user_prompt="First prompt", run_id="batch-run-1"),
        InputPromptRecord(user_prompt="Second prompt", run_id="batch-run-2"),
    ]
    deps = SimpleNamespace(
        uuid_factory=lambda: "unused-run-id",
        logger=logging.getLogger("test-input-file-support"),
    )
    called_run_ids: list[str] = []

    def fake_run_once(user_prompt: str, **kwargs: object) -> dict[str, str]:
        run_id = str(kwargs["run_id"])
        called_run_ids.append(run_id)
        if run_id == "batch-run-1":
            raise RuntimeError("router exploded")
        return {"run_id": run_id, "run_status": "succeeded"}

    monkeypatch.setattr(run_module, "run_once", fake_run_once)

    summary = run_module.run_batch(records, input_file="examples/prompts.sample.json", deps=deps)

    assert called_run_ids == ["batch-run-1", "batch-run-2"]
    assert summary == {
        "input_file": "examples/prompts.sample.json",
        "total_records": 2,
        "succeeded": 1,
        "partial": 0,
        "dry_run": 0,
        "failed": 1,
        "run_ids": ["batch-run-1", "batch-run-2"],
    }


def test_main_returns_nonzero_and_prints_summary_for_partial_batch(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pipelines.workflows.image_prompt_gen import run as run_module

    monkeypatch.setattr(run_module, "load_input_records", lambda path: [object()])
    monkeypatch.setattr(
        run_module,
        "run_batch",
        lambda records, **kwargs: {
            "input_file": kwargs["input_file"],
            "total_records": 1,
            "succeeded": 0,
            "partial": 1,
            "dry_run": 0,
            "failed": 0,
            "run_ids": ["partial-run"],
        },
    )

    exit_code = run_module.main(["--input-file", "examples/prompts.sample.json"])

    assert exit_code == 1
    assert json.loads(capsys.readouterr().out) == {
        "input_file": "examples/prompts.sample.json",
        "total_records": 1,
        "succeeded": 0,
        "partial": 1,
        "dry_run": 0,
        "failed": 0,
        "run_ids": ["partial-run"],
    }
