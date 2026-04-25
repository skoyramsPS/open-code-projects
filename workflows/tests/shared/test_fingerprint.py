from __future__ import annotations

from dataclasses import dataclass

import pytest

from comicbook.fingerprint import compute_prompt_fingerprint as legacy_compute_prompt_fingerprint
from comicbook.fingerprint import materialize_rendered_prompts as legacy_materialize_rendered_prompts
from pipelines.shared.fingerprint import compute_prompt_fingerprint, materialize_rendered_prompts, render_prompt_text


@dataclass(frozen=True)
class TemplateStub:
    style_text: str


@dataclass(frozen=True)
class PromptStub:
    subject_text: str
    template_ids: list[str]
    size: str
    quality: str
    image_model: str


@dataclass(frozen=True)
class PlanStub:
    prompts: list[PromptStub]


def test_legacy_wrapper_points_to_shared_fingerprint_module() -> None:
    assert legacy_compute_prompt_fingerprint is compute_prompt_fingerprint
    assert legacy_materialize_rendered_prompts is materialize_rendered_prompts


def test_compute_prompt_fingerprint_is_deterministic() -> None:
    first = compute_prompt_fingerprint(
        "Soft painterly linework.\n\n---\n\nTraveler portrait at sunrise.",
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
    )
    second = compute_prompt_fingerprint(
        "Soft painterly linework.\n\n---\n\nTraveler portrait at sunrise.",
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
    )

    assert first == second


def test_render_prompt_text_joins_templates_in_order() -> None:
    rendered = render_prompt_text(
        "Traveler portrait at sunrise.",
        [
            TemplateStub("Soft painterly linework."),
            TemplateStub("Golden-hour rim light."),
        ],
    )

    assert rendered == (
        "Soft painterly linework.\n\n"
        "Golden-hour rim light.\n\n"
        "---\n\n"
        "Traveler portrait at sunrise."
    )


def test_materialize_rendered_prompts_builds_rendered_prompt_models() -> None:
    plan = PlanStub(
        prompts=[
            PromptStub(
                subject_text="Traveler walking through a lantern-lit alley.",
                template_ids=["storybook-soft", "inked-contrast"],
                size="1024x1536",
                quality="high",
                image_model="gpt-image-1.5",
            )
        ]
    )

    rendered_prompts = materialize_rendered_prompts(
        plan=plan,
        template_lookup={
            "storybook-soft": TemplateStub("Soft painterly linework and warm golden light."),
            "inked-contrast": TemplateStub("Bold black inks with crisp silhouette contrast."),
        },
    )

    assert len(rendered_prompts) == 1
    assert rendered_prompts[0].template_ids == ["storybook-soft", "inked-contrast"]
    assert rendered_prompts[0].rendered_prompt == (
        "Soft painterly linework and warm golden light.\n\n"
        "Bold black inks with crisp silhouette contrast.\n\n"
        "---\n\n"
        "Traveler walking through a lantern-lit alley."
    )
    assert rendered_prompts[0].fingerprint == compute_prompt_fingerprint(
        rendered_prompts[0].rendered_prompt,
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
    )


def test_materialize_rendered_prompts_rejects_missing_template_records() -> None:
    plan = PlanStub(
        prompts=[
            PromptStub(
                subject_text="Traveler walking through a lantern-lit alley.",
                template_ids=["missing-template"],
                size="1024x1536",
                quality="high",
                image_model="gpt-image-1.5",
            )
        ]
    )

    with pytest.raises(ValueError, match="Missing template records"):
        materialize_rendered_prompts(plan=plan, template_lookup={})
