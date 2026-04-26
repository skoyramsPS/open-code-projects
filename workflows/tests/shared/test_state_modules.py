from __future__ import annotations

from typing import Any, get_args, get_type_hints

from pipelines.shared import state as shared_state
from pipelines.workflows.image_prompt_gen import state as image_state
from pipelines.workflows.template_upload import state as upload_state


def test_state_modules_split_symbols_by_workflow_ownership() -> None:
    assert image_state.TemplateSummary.__module__ == "pipelines.workflows.image_prompt_gen.state"
    assert image_state.RouterPlan.__module__ == "pipelines.workflows.image_prompt_gen.state"
    assert image_state.RenderedPrompt.__module__ == "pipelines.workflows.image_prompt_gen.state"
    assert upload_state.ImportRunState.__module__ == "pipelines.workflows.template_upload.state"
    assert upload_state.TemplateImportRow.__module__ == "pipelines.workflows.template_upload.state"
    assert shared_state.WorkflowError.__module__ == "pipelines.shared.state"
    assert shared_state.UsageTotals.__module__ == "pipelines.shared.state"
    assert shared_state.RunSummary.__module__ == "pipelines.shared.state"


def test_workflow_state_modules_reuse_shared_base_types() -> None:
    image_hints = get_type_hints(image_state.RunState, globalns=vars(image_state), localns=vars(image_state))
    upload_hints = get_type_hints(upload_state.ImportRunState, globalns=vars(upload_state), localns=vars(upload_state))

    assert image_hints["usage"] is shared_state.UsageTotals
    assert get_args(image_hints["errors"])[0] is shared_state.WorkflowError
    assert image_hints["summary"] is shared_state.RunSummary
    assert upload_hints["usage"] is shared_state.UsageTotals
    assert get_args(upload_hints["errors"])[0] is shared_state.WorkflowError


def test_split_state_models_validate_known_good_payloads() -> None:
    template = image_state.TemplateSummary.model_validate(
        {
            "id": "storybook-soft",
            "name": "Storybook Soft",
            "tags": ["storybook", "warm"],
            "summary": "Soft painterly lighting and warm illustration tones.",
            "created_at": "2026-04-23T12:00:00Z",
        }
    )
    draft = image_state.NewTemplateDraft.model_validate(
        {
            "id": "sunlit-portrait",
            "name": "Sunlit Portrait",
            "style_text": "Warm, bright, painterly portrait treatment.",
            "tags": ["portrait", "warm"],
            "summary": "Portrait style with bright storybook warmth.",
        }
    )
    plan = image_state.RouterPlan.model_validate(
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
    rendered = image_state.RenderedPrompt.model_validate(
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
    result = image_state.ImageResult.model_validate(
        {
            "fingerprint": "abc123",
            "status": "generated",
            "file_path": "image_output/run-1/001.png",
            "bytes": 42,
            "run_id": "run-1",
            "created_at": "2026-04-23T12:00:10Z",
        }
    )
    error = shared_state.WorkflowError.model_validate(
        {
            "code": "content_filter",
            "message": "The image request was blocked.",
            "node": "generate_images_serial",
            "retryable": False,
        }
    )
    usage = shared_state.UsageTotals.model_validate(
        {
            "router_calls": 1,
            "router_input_tokens": 120,
            "router_output_tokens": 45,
            "image_calls": 1,
            "estimated_cost_usd": 0.24,
        }
    )
    summary = shared_state.RunSummary.model_validate(
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

    parsed_row: upload_state.TemplateImportRow = {
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
    row_result: upload_state.TemplateImportRowResult = {
        "row_index": 0,
        "template_id": "storybook-soft",
        "status": "inserted",
        "reason": None,
        "warnings": [],
        "diff": None,
        "retry_count": 0,
    }
    import_state: upload_state.ImportRunState = {
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
        "usage": shared_state.UsageTotals(),
        "errors": [],
        "run_status": "running",
        "report_path": None,
    }

    assert isinstance(plan.template_decision, image_state.RouterTemplateDecision)
    assert rendered.image_model == "gpt-image-1.5"
    assert result.status == "generated"
    assert error.code == "content_filter"
    assert usage.estimated_cost_usd == 0.24
    assert summary.run_status == "succeeded"
    assert import_state["parsed_rows"][0]["write_mode"] == "insert"
