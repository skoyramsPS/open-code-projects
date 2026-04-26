"""Cross-workflow state and schema contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RunStatus = Literal["running", "succeeded", "partial", "failed", "dry_run", "cancelled"]


class WorkflowModel(BaseModel):
    """Base model that rejects undeclared fields by default."""

    model_config = ConfigDict(extra="forbid")


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


__all__ = [
    "RunStatus",
    "RunSummary",
    "UsageTotals",
    "WorkflowError",
    "WorkflowModel",
]
