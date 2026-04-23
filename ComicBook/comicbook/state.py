"""Workflow state and schema contracts."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ImageSize = Literal["1024x1024", "1024x1536", "1536x1024"]
ImageQuality = Literal["low", "medium", "high", "auto"]
RouterModel = Literal["gpt-5.4", "gpt-5.4-mini"]
RunStatus = Literal["running", "succeeded", "partial_success", "failed", "dry_run", "cancelled"]
ImageResultStatus = Literal["generated", "cached", "failed", "skipped_rate_limit"]


class WorkflowModel(BaseModel):
    """Base model that rejects undeclared fields by default."""

    model_config = ConfigDict(extra="forbid")


class TemplateSummary(WorkflowModel):
    id: str
    name: str
    tags: list[str] = Field(default_factory=list)
    summary: str
    created_at: str | None = None


class NewTemplateDraft(WorkflowModel):
    id: str
    name: str
    style_text: str
    tags: list[str] = Field(default_factory=list)
    summary: str
    supersedes_id: str | None = None

    @field_validator("id")
    @classmethod
    def _slug_must_be_lowercase(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError("new_template.id must be a lowercase slug")
        return value


class PromptPlanItem(WorkflowModel):
    subject_text: str
    template_ids: list[str] = Field(default_factory=list)
    size: ImageSize = "1024x1536"
    quality: ImageQuality = "high"
    image_model: str = "gpt-image-1.5"

    @field_validator("subject_text", "image_model")
    @classmethod
    def _require_non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class RouterTemplateDecision(WorkflowModel):
    selected_template_ids: list[str] = Field(default_factory=list)
    extract_new_template: bool = False
    new_template: NewTemplateDraft | None = None

    @model_validator(mode="after")
    def _validate_extraction_pairing(self) -> "RouterTemplateDecision":
        if self.extract_new_template and self.new_template is None:
            raise ValueError("new_template is required when extract_new_template is true")
        if not self.extract_new_template and self.new_template is not None:
            raise ValueError("new_template must be omitted when extract_new_template is false")
        return self


class RouterPlan(WorkflowModel):
    router_model_chosen: RouterModel
    rationale: str = Field(max_length=600)
    needs_escalation: bool = False
    escalation_reason: str | None = None
    template_decision: RouterTemplateDecision
    prompts: list[PromptPlanItem] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _validate_escalation_reason(self) -> "RouterPlan":
        if self.needs_escalation and not self.escalation_reason:
            raise ValueError("escalation_reason is required when needs_escalation is true")
        return self


class RenderedPrompt(WorkflowModel):
    fingerprint: str | None = None
    subject_text: str
    template_ids: list[str] = Field(default_factory=list)
    size: ImageSize
    quality: ImageQuality
    image_model: str
    rendered_prompt: str


class ImageResult(WorkflowModel):
    fingerprint: str
    status: ImageResultStatus
    file_path: str | None = None
    bytes: int = 0
    run_id: str | None = None
    created_at: str | None = None
    failure_reason: str | None = None


class WorkflowError(WorkflowModel):
    code: str
    message: str
    node: str | None = None
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class UsageTotals(WorkflowModel):
    router_calls: int = 0
    router_input_tokens: int = 0
    router_output_tokens: int = 0
    image_calls: int = 0
    estimated_cost_usd: float = 0.0


class RunSummary(WorkflowModel):
    run_id: str
    run_status: RunStatus
    started_at: str
    ended_at: str | None = None
    cache_hits: int = 0
    generated: int = 0
    failed: int = 0
    skipped_rate_limit: int = 0
    est_cost_usd: float = 0.0
    router_model: str | None = None
    router_escalated: bool = False


class RunState(TypedDict, total=False):
    """Shared graph state contract used across workflow phases."""

    run_id: str
    user_prompt: str
    dry_run: bool
    force_regenerate: bool
    exact_image_count: int | None
    budget_usd: float | None
    redact_prompts: bool
    started_at: str
    templates: list[TemplateSummary]
    template_catalog_size: int
    templates_sent_to_router: list[TemplateSummary]
    router_model: str
    plan: RouterPlan
    plan_raw: dict[str, Any] | str
    plan_repair_attempts: int
    router_escalated: bool
    rendered_prompts: list[RenderedPrompt]
    rendered_prompts_by_fp: dict[str, RenderedPrompt]
    cache_hits: list[RenderedPrompt]
    to_generate: list[RenderedPrompt]
    image_results: list[ImageResult]
    errors: list[WorkflowError]
    rate_limit_consecutive_failures: int
    usage: UsageTotals
    ended_at: str
    summary: RunSummary
    run_status: str


__all__ = [
    "ImageQuality",
    "ImageResult",
    "ImageResultStatus",
    "ImageSize",
    "NewTemplateDraft",
    "PromptPlanItem",
    "RenderedPrompt",
    "RouterModel",
    "RouterPlan",
    "RouterTemplateDecision",
    "RunState",
    "RunStatus",
    "RunSummary",
    "TemplateSummary",
    "UsageTotals",
    "WorkflowError",
]
