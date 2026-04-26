from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from pipelines.shared.config import AppConfig, ConfigError, load_config
from pipelines.shared.state import RunSummary, UsageTotals, WorkflowError
from pipelines.workflows.image_prompt_gen.state import (
    ImageResult,
    NewTemplateDraft,
    RenderedPrompt,
    RouterPlan,
    RouterTemplateDecision,
    TemplateSummary,
)
from pipelines.workflows.template_upload.state import (
    ImportRowStatus,
    ImportRunState,
    TemplateImportRow,
    TemplateImportRowResult,
)


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


def test_target_tree_load_config_reads_dotenv_defaults_and_budget_flags(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com/",
                "AZURE_OPENAI_API_KEY=test-key",
                "AZURE_OPENAI_API_VERSION=2025-04-01-preview",
                "AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-router",
                "AZURE_OPENAI_IMAGE_DEPLOYMENT=gpt-image-1.5",
                "COMICBOOK_DAILY_BUDGET_USD=12.5",
                "COMICBOOK_ENABLE_ROUTER_PREFLIGHT=1",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(dotenv_path=dotenv_path)

    assert isinstance(config, AppConfig)
    assert config.azure_openai_endpoint == "https://example.openai.azure.com"
    assert config.azure_openai_api_key.get_secret_value() == "test-key"
    assert config.azure_openai_chat_deployment == "gpt-5-router"
    assert config.azure_openai_image_deployment == "gpt-image-1.5"
    assert config.comicbook_db_path == Path("./comicbook.sqlite")
    assert config.comicbook_image_output_dir == Path("./image_output")
    assert config.comicbook_runs_dir == Path("./runs")
    assert config.comicbook_logs_dir == Path("./logs")
    assert config.comicbook_import_max_rows_per_file == 1000
    assert config.comicbook_import_max_file_bytes == 5_000_000
    assert config.comicbook_import_allow_external_path is False
    assert config.comicbook_import_backfill_model == "gpt-5.4-mini"
    assert config.comicbook_router_model_fallback == "gpt-5.4-mini"
    assert config.comicbook_router_model_escalation == "gpt-5.4"
    assert config.comicbook_router_prompt_version == "ROUTER_SYSTEM_PROMPT_V2"
    assert config.comicbook_daily_budget_usd == 12.5
    assert config.comicbook_enable_router_preflight is True


def test_target_tree_load_config_reads_upload_guardrail_overrides(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com/",
                "AZURE_OPENAI_API_KEY=test-key",
                "AZURE_OPENAI_API_VERSION=2025-04-01-preview",
                "AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-router",
                "AZURE_OPENAI_IMAGE_DEPLOYMENT=gpt-image-1.5",
                "COMICBOOK_IMPORT_MAX_ROWS_PER_FILE=42",
                "COMICBOOK_IMPORT_MAX_FILE_BYTES=2048",
                "COMICBOOK_IMPORT_ALLOW_EXTERNAL_PATH=true",
                "COMICBOOK_IMPORT_BACKFILL_MODEL=gpt-5.4",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(dotenv_path=dotenv_path)

    assert config.comicbook_import_max_rows_per_file == 42
    assert config.comicbook_import_max_file_bytes == 2048
    assert config.comicbook_import_allow_external_path is True
    assert config.comicbook_import_backfill_model == "gpt-5.4"


def test_target_tree_load_config_rejects_missing_required_settings(tmp_path: Path) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com\n", encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        load_config(dotenv_path=dotenv_path)

    message = str(excinfo.value)
    assert "AZURE_OPENAI_API_KEY" in message
    assert "AZURE_OPENAI_CHAT_DEPLOYMENT" in message
    assert "AZURE_OPENAI_IMAGE_DEPLOYMENT" in message


def test_target_tree_compat_state_models_validate_known_good_payload() -> None:
    template = TemplateSummary.model_validate(
        {
            "id": "storybook-soft",
            "name": "Storybook Soft",
            "tags": ["storybook", "warm"],
            "summary": "Soft painterly lighting and warm illustration tones.",
            "created_at": "2026-04-23T12:00:00Z",
        }
    )
    draft = NewTemplateDraft.model_validate(
        {
            "id": "sunlit-portrait",
            "name": "Sunlit Portrait",
            "style_text": "Warm, bright, painterly portrait treatment.",
            "tags": ["portrait", "warm"],
            "summary": "Portrait style with bright storybook warmth.",
        }
    )
    plan = RouterPlan.model_validate(
        {
            "router_model_chosen": "gpt-5.4-mini",
            "rationale": "The prompt already maps cleanly to the known storybook template.",
            "template_decision": {
                "selected_template_ids": [template.id],
                "extract_new_template": True,
                "new_template": draft.model_dump(),
            },
            "prompts": [
                {
                    "subject_text": "Heroic portrait of a traveler at sunrise.",
                    "template_ids": [template.id, draft.id],
                    "size": "1024x1536",
                    "quality": "high",
                    "image_model": "gpt-image-1.5",
                }
            ],
        }
    )
    rendered = RenderedPrompt.model_validate(
        {
            "fingerprint": "abc123",
            "subject_text": "Heroic portrait of a traveler at sunrise.",
            "template_ids": [template.id, draft.id],
            "size": "1024x1536",
            "quality": "high",
            "image_model": "gpt-image-1.5",
            "rendered_prompt": "style\n\n---\n\nsubject",
        }
    )
    result = ImageResult.model_validate(
        {
            "fingerprint": "abc123",
            "status": "generated",
            "file_path": "image_output/run-1/001.png",
            "bytes": 42,
            "run_id": "run-1",
            "created_at": "2026-04-23T12:00:10Z",
        }
    )
    error = WorkflowError.model_validate(
        {
            "code": "content_filter",
            "message": "The image request was blocked.",
            "node": "generate_images_serial",
            "retryable": False,
        }
    )
    usage = UsageTotals.model_validate(
        {
            "router_calls": 1,
            "router_input_tokens": 120,
            "router_output_tokens": 45,
            "image_calls": 1,
            "estimated_cost_usd": 0.24,
        }
    )
    summary = RunSummary.model_validate(
        {
            "run_id": "run-1",
            "run_status": "succeeded",
            "started_at": "2026-04-23T12:00:00Z",
            "ended_at": "2026-04-23T12:00:20Z",
            "cache_hits": 0,
            "generated": 1,
            "failed": 0,
            "skipped_rate_limit": 0,
            "est_cost_usd": 0.24,
            "router_model": plan.router_model_chosen,
            "router_escalated": False,
        }
    )

    assert template.tags == ["storybook", "warm"]
    assert isinstance(plan.template_decision, RouterTemplateDecision)
    assert plan.prompts[0].template_ids == [template.id, draft.id]
    assert rendered.image_model == "gpt-image-1.5"
    assert result.status == "generated"
    assert error.code == "content_filter"
    assert usage.estimated_cost_usd == pytest.approx(0.24)
    assert summary.run_status == "succeeded"


def test_target_tree_upload_state_contract_symbols_are_available_via_compat_wrapper() -> None:
    assert set(get_args(ImportRowStatus)) == {
        "inserted",
        "updated",
        "failed",
        "skipped_resume",
        "skipped_duplicate",
        "dry_run_ok",
    }

    parsed_row: TemplateImportRow = {
        "row_index": 0,
        "template_id": "storybook-soft",
        "name": "Storybook Soft",
        "style_text": "Soft painterly linework.",
        "tags": [],
        "summary": "Warm storybook lighting.",
        "requested_supersedes_id": None,
        "resolved_supersedes_id": None,
        "validation_errors": [],
        "warnings": [],
        "needs_backfill_tags": False,
        "needs_backfill_summary": False,
        "backfill_raw": None,
        "write_mode": "insert",
        "retry_count": 0,
    }
    row_result: TemplateImportRowResult = {
        "row_index": 0,
        "template_id": "storybook-soft",
        "status": "inserted",
        "reason": None,
        "warnings": [],
        "diff": None,
        "retry_count": 0,
    }
    import_state: ImportRunState = {
        "import_run_id": "import-run-1",
        "source_file_path": "templates.json",
        "source_label": "templates.json",
        "source_file_hash": "hash-123",
        "input_version": 1,
        "dry_run": False,
        "no_backfill": False,
        "allow_missing_optional": False,
        "allow_external_path": False,
        "budget_usd": None,
        "redact_style_text_in_logs": False,
        "started_at": "2026-04-23T12:00:00Z",
        "raw_rows": [],
        "parsed_rows": [parsed_row],
        "rows_to_process": [0],
        "deferred_rows": [],
        "rows_skipped_by_resume": [],
        "row_results": [row_result],
        "usage": UsageTotals(),
        "errors": [],
        "run_status": "running",
        "report_path": None,
    }

    assert import_state["parsed_rows"][0]["write_mode"] == "insert"
    assert import_state["row_results"][0]["status"] == "inserted"


def test_target_tree_new_template_draft_requires_lowercase_slug() -> None:
    with pytest.raises(ValidationError):
        NewTemplateDraft.model_validate(
            {
                "id": "Not-Lowercase",
                "name": "Broken",
                "style_text": "Painterly",
                "tags": [],
                "summary": "Invalid slug example.",
            }
        )
