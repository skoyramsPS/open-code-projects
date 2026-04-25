"""Load template summaries and apply deterministic router pre-filtering."""

from __future__ import annotations

from comicbook.state import RunState

from pipelines.shared.deps import Deps
from pipelines.workflows.image_prompt_gen.prompts.router_prompts import select_templates_for_router


def load_templates(state: RunState, deps: Deps) -> dict[str, object]:
    """Load the full template catalog and the router-visible subset."""

    user_prompt = state.get("user_prompt")
    if not user_prompt:
        raise ValueError("load_templates requires state['user_prompt']")

    templates = deps.db.list_template_summaries()
    templates_sent_to_router = select_templates_for_router(user_prompt=user_prompt, templates=templates)

    return {
        "templates": templates,
        "template_catalog_size": len(templates),
        "templates_sent_to_router": templates_sent_to_router,
    }


__all__ = ["load_templates"]
