from __future__ import annotations

import json
import logging
import sys
from types import SimpleNamespace

import pytest

from pipelines.shared.logging import JsonFormatter, get_logger, log_event, log_node_event


@pytest.fixture(autouse=True)
def reset_pipelines_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIPELINES_LOG_FORMAT", raising=False)
    monkeypatch.delenv("PIPELINES_LOG_LEVEL", raising=False)

    root = logging.getLogger("pipelines")
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    if hasattr(root, "_pipelines_logging_configured"):
        delattr(root, "_pipelines_logging_configured")
    root.setLevel(logging.NOTSET)
    root.propagate = True


def test_json_formatter_promotes_standard_fields_and_nests_extra_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="pipelines.workflows.image_prompt_gen.run",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="run started",
        args=(),
        exc_info=None,
    )
    record.event = "run_started"
    record.workflow = "image_prompt_gen"
    record.run_id = "run-123"
    record.component = "cli"
    record.duration_ms = 12
    record.prompt_count = 3

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "pipelines.workflows.image_prompt_gen.run"
    assert payload["event"] == "run_started"
    assert payload["workflow"] == "image_prompt_gen"
    assert payload["run_id"] == "run-123"
    assert payload["message"] == "run started"
    assert payload["component"] == "cli"
    assert payload["duration_ms"] == 12
    assert payload["extra"] == {"prompt_count": 3}
    assert payload["timestamp"].endswith("+00:00")


def test_json_formatter_serializes_exceptions_and_promotes_error_fields() -> None:
    formatter = JsonFormatter()

    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="pipelines.shared.db",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="query failed",
        args=(),
        exc_info=exc_info,
    )
    record.event = "query_failed"
    record.workflow = "shared"
    record.run_id = None
    record.error = {"code": "db_error", "message": "boom", "retryable": False}
    record.statement = "select 1"

    payload = json.loads(formatter.format(record))

    assert payload["event"] == "query_failed"
    assert payload["error.code"] == "db_error"
    assert payload["error.message"] == "boom"
    assert payload["error.retryable"] is False
    assert "ValueError: boom" in payload["exc_info"]
    assert payload["extra"] == {"statement": "select 1"}


def test_log_event_emits_json_by_default_with_non_promoted_fields_nested(capsys: pytest.CaptureFixture[str]) -> None:
    logger = get_logger("pipelines.shared.runtime")

    log_event(
        logger,
        "cli_started",
        workflow="shared",
        run_id=None,
        component="cli",
        attempt=2,
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert payload["event"] == "cli_started"
    assert payload["workflow"] == "shared"
    assert payload["run_id"] is None
    assert payload["component"] == "cli"
    assert payload["message"] == "cli_started"
    assert payload["extra"] == {"attempt": 2}


def test_log_node_event_infers_workflow_run_id_and_node(capsys: pytest.CaptureFixture[str]) -> None:
    logger = get_logger("pipelines.workflows.image_prompt_gen.nodes.router")
    deps = SimpleNamespace(logger=logger, workflow="image_prompt_gen")
    state = {"run_id": "run-456"}

    def router_node() -> None:
        log_node_event(deps, state, "node_started", template_count=4)

    router_node()

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())

    assert payload["event"] == "node_started"
    assert payload["workflow"] == "image_prompt_gen"
    assert payload["run_id"] == "run-456"
    assert payload["node"] == "router_node"
    assert payload["extra"] == {"template_count": 4}


def test_get_logger_is_idempotent_and_text_mode_is_opt_in(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    logger_one = get_logger("pipelines.shared.one")
    logger_two = get_logger("pipelines.shared.two")
    root = logging.getLogger("pipelines")

    assert logger_one.name == "pipelines.shared.one"
    assert logger_two.name == "pipelines.shared.two"
    assert len(root.handlers) == 1

    log_event(logger_one, "json_mode_check")
    json_output = capsys.readouterr().out.strip()
    assert json.loads(json_output)["event"] == "json_mode_check"

    monkeypatch.setenv("PIPELINES_LOG_FORMAT", "text")
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    if hasattr(root, "_pipelines_logging_configured"):
        delattr(root, "_pipelines_logging_configured")

    text_logger = get_logger("pipelines.shared.text")
    log_event(text_logger, "text_mode_check")
    text_output = capsys.readouterr().out.strip()

    assert text_output
    assert not text_output.startswith("{")
    assert "text_mode_check" in text_output
