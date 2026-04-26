"""Legacy compatibility wrapper for the split workflow state modules."""

from __future__ import annotations

import sys
from pathlib import Path

WORKFLOWS_ROOT = Path(__file__).resolve().parents[2] / "workflows"

if str(WORKFLOWS_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOWS_ROOT))

from pipelines.shared.state import RunStatus, RunSummary, UsageTotals, WorkflowError, WorkflowModel
from pipelines.workflows.image_prompt_gen.state import (
    ImageQuality,
    ImageResult,
    ImageResultStatus,
    ImageSize,
    NewTemplateDraft,
    PromptPlanItem,
    RenderedPrompt,
    RouterModel,
    RouterPlan,
    RouterTemplateDecision,
    RunState,
    TemplateSummary,
)
from pipelines.workflows.template_upload.state import (
    ImportRowStatus,
    ImportRunState,
    ImportWriteMode,
    TemplateImportRow,
    TemplateImportRowResult,
)


__all__ = [
    "ImportRowStatus",
    "ImportRunState",
    "ImportWriteMode",
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
    "TemplateImportRow",
    "TemplateImportRowResult",
    "TemplateSummary",
    "UsageTotals",
    "WorkflowError",
    "WorkflowModel",
]
