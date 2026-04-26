"""Materialize prompts, persist prompt rows, and partition cache hits."""

from __future__ import annotations

from collections.abc import Sequence

from pipelines.shared.db import ImageRecord, TemplateRecord
from pipelines.shared.deps import Deps
from pipelines.shared.fingerprint import materialize_rendered_prompts
from pipelines.workflows.image_prompt_gen.nodes import instrument_image_node
from pipelines.workflows.image_prompt_gen.state import RenderedPrompt, RunState


def _dedupe_preserving_order(values: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _collect_plan_template_ids(state: RunState) -> list[str]:
    plan = state["plan"]
    template_ids: list[str] = []
    for prompt in plan.prompts:
        template_ids.extend(prompt.template_ids)
    return _dedupe_preserving_order(template_ids)


def _has_successful_image(existing_images: Sequence[ImageRecord]) -> bool:
    return any(image.status == "generated" and image.file_path for image in existing_images)


def _resolve_template_lookup(state: RunState, deps: Deps) -> dict[str, TemplateRecord]:
    if "templates" not in state:
        raise ValueError("cache_lookup requires state['templates']")

    requested_template_ids = _collect_plan_template_ids(state)
    known_template_ids = {template.id for template in state["templates"]}
    unknown_template_ids = [template_id for template_id in requested_template_ids if template_id not in known_template_ids]
    if unknown_template_ids:
        raise ValueError("cache_lookup plan referenced template ids outside state['templates']")

    template_rows = deps.db.get_templates_by_ids(requested_template_ids)
    return {row.id: row for row in template_rows}


@instrument_image_node(
    "cache_lookup",
    complete_fields=lambda _state, delta: {
        "rendered_prompt_count": len(delta.get("rendered_prompts", [])),
        "cache_hit_count": len(delta.get("cache_hits", [])),
        "to_generate_count": len(delta.get("to_generate", [])),
    },
)
def cache_lookup(state: RunState, deps: Deps) -> dict[str, object]:
    """Persist prompt rows and split ordered prompt work into cache hits vs generation."""

    if "plan" not in state:
        raise ValueError("cache_lookup requires state['plan']")

    run_id = state.get("run_id")
    if not run_id:
        raise ValueError("cache_lookup requires state['run_id']")

    started_at = state.get("started_at")
    if not started_at:
        raise ValueError("cache_lookup requires state['started_at']")

    template_lookup = _resolve_template_lookup(state, deps)
    rendered_prompts = materialize_rendered_prompts(
        plan=state["plan"],
        template_lookup=template_lookup,
        prompt_factory=RenderedPrompt.model_validate,
    )

    rendered_prompts_by_fp: dict[str, RenderedPrompt] = {}
    cache_hits: list[RenderedPrompt] = []
    to_generate: list[RenderedPrompt] = []
    force_regenerate = state.get("force_regenerate", False)

    for prompt in rendered_prompts:
        fingerprint = prompt.fingerprint
        if fingerprint is None:  # pragma: no cover - defensive after materialization
            raise RuntimeError("cache_lookup requires prompts with computed fingerprints")

        deps.db.upsert_prompt_if_absent(prompt=prompt, first_seen_run=run_id, created_at=started_at)

        if fingerprint in rendered_prompts_by_fp:
            continue

        rendered_prompts_by_fp[fingerprint] = prompt
        existing_images = deps.db.get_existing_images_by_fingerprint(fingerprint)
        if not force_regenerate and _has_successful_image(existing_images):
            cache_hits.append(prompt)
        else:
            to_generate.append(prompt)

    return {
        "rendered_prompts": rendered_prompts,
        "rendered_prompts_by_fp": rendered_prompts_by_fp,
        "cache_hits": cache_hits,
        "to_generate": to_generate,
    }


__all__ = ["cache_lookup"]
