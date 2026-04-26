"""Deterministic prompt materialization and fingerprint helpers."""

from __future__ import annotations

import hashlib
from typing import Callable, Mapping, Protocol, Sequence, TypeVar


class TemplateLike(Protocol):
    style_text: str


class PromptLike(Protocol):
    subject_text: str
    template_ids: Sequence[str]
    size: str
    quality: str
    image_model: str


class PlanLike(Protocol):
    prompts: Sequence[PromptLike]


TPrompt = TypeVar("TPrompt")


def render_prompt_text(subject_text: str, ordered_templates: Sequence[TemplateLike]) -> str:
    """Compose the final rendered prompt from ordered template style text blocks."""

    style_block = "\n\n".join(template.style_text for template in ordered_templates)
    return f"{style_block}\n\n---\n\n{subject_text}" if style_block else subject_text


def compute_prompt_fingerprint(rendered_prompt: str, *, size: str, quality: str, image_model: str) -> str:
    """Return the stable fingerprint for a rendered prompt input tuple."""

    material = f"{rendered_prompt}{size}{quality}{image_model}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def materialize_rendered_prompts(
    *,
    plan: PlanLike,
    template_lookup: Mapping[str, TemplateLike],
    prompt_factory: Callable[[dict[str, object]], TPrompt],
) -> list[TPrompt]:
    """Render prompt text and fingerprints from a validated router plan."""

    rendered_prompts: list[TPrompt] = []
    for prompt in plan.prompts:
        missing_template_ids = [template_id for template_id in prompt.template_ids if template_id not in template_lookup]
        if missing_template_ids:
            joined_ids = ", ".join(missing_template_ids)
            raise ValueError(f"Missing template records for prompt composition: {joined_ids}")

        ordered_templates = [template_lookup[template_id] for template_id in prompt.template_ids]
        rendered_prompt = render_prompt_text(prompt.subject_text, ordered_templates)
        rendered_prompts.append(
            prompt_factory(
                {
                    "fingerprint": compute_prompt_fingerprint(
                        rendered_prompt,
                        size=prompt.size,
                        quality=prompt.quality,
                        image_model=prompt.image_model,
                    ),
                    "subject_text": prompt.subject_text,
                    "template_ids": list(prompt.template_ids),
                    "size": prompt.size,
                    "quality": prompt.quality,
                    "image_model": prompt.image_model,
                    "rendered_prompt": rendered_prompt,
                }
            )
        )
    return rendered_prompts


__all__ = [
    "compute_prompt_fingerprint",
    "materialize_rendered_prompts",
    "render_prompt_text",
]
