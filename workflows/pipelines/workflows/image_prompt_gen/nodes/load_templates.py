"""Load template summaries and apply deterministic router pre-filtering."""

from __future__ import annotations

from pipelines.shared.deps import Deps
from pipelines.shared.db import TemplateRecord
from pipelines.workflows.image_prompt_gen.nodes import instrument_image_node
from pipelines.workflows.image_prompt_gen.state import RunState, TemplateSummary
from pipelines.workflows.image_prompt_gen.prompts.router_prompts import select_templates_for_router


def _to_template_summary(record: TemplateRecord) -> TemplateSummary:
    return TemplateSummary.model_validate(
        {
            "id": record.id,
            "name": record.name,
            "tags": record.tags,
            "summary": record.summary,
            "created_at": record.created_at,
        }
    )


@instrument_image_node(
    "load_templates",
    complete_fields=lambda _state, delta: {
        "template_catalog_size": delta.get("template_catalog_size"),
        "templates_sent_to_router": len(delta.get("templates_sent_to_router", [])),
    },
)
def load_templates(state: RunState, deps: Deps) -> dict[str, object]:
    """Load the full template catalog and the router-visible subset."""

    user_prompt = state.get("user_prompt")
    if not user_prompt:
        raise ValueError("load_templates requires state['user_prompt']")

    templates = deps.db.list_template_summaries(summary_factory=_to_template_summary)
    templates_sent_to_router = select_templates_for_router(user_prompt=user_prompt, templates=templates)

    return {
        "templates": templates,
        "template_catalog_size": len(templates),
        "templates_sent_to_router": templates_sent_to_router,
    }


__all__ = ["load_templates"]
