from __future__ import annotations

from comicbook.router_prompts import (
    ROUTER_SYSTEM_PROMPT_V2,
    RouterValidationError,
    select_templates_for_router,
    validate_router_plan,
)
from comicbook.state import TemplateSummary


def make_template(template_id: str, *, name: str, tags: list[str], summary: str, created_at: str) -> TemplateSummary:
    return TemplateSummary.model_validate(
        {
            "id": template_id,
            "name": name,
            "tags": tags,
            "summary": summary,
            "created_at": created_at,
        }
    )


def test_validate_router_plan_redacts_potential_prompt_leak() -> None:
    template = make_template(
        "storybook-soft",
        name="Storybook Soft",
        tags=["storybook", "warm"],
        summary="Soft painterly storybook lighting.",
        created_at="2026-04-23T12:00:00Z",
    )

    plan = validate_router_plan(
        {
            "router_model_chosen": "gpt-5.4-mini",
            "rationale": f"The answer follows: {ROUTER_SYSTEM_PROMPT_V2[:40]} ...",
            "template_decision": {
                "selected_template_ids": [template.id],
                "extract_new_template": False,
                "new_template": None,
            },
            "prompts": [
                {
                    "subject_text": "Hero portrait of a traveler crossing a glowing forest bridge at sunrise.",
                    "template_ids": [template.id],
                    "size": "1024x1536",
                    "quality": "high",
                    "image_model": "gpt-image-1.5",
                }
            ],
        },
        available_templates=[template],
        exact_image_count=1,
    )

    assert plan.template_decision.selected_template_ids == [template.id]
    assert plan.rationale == "[redacted: potential prompt-leak]"


def test_validate_router_plan_rejects_unknown_template_ids() -> None:
    template = make_template(
        "storybook-soft",
        name="Storybook Soft",
        tags=["storybook"],
        summary="Soft painterly storybook lighting.",
        created_at="2026-04-23T12:00:00Z",
    )

    try:
        validate_router_plan(
            {
                "router_model_chosen": "gpt-5.4-mini",
                "rationale": "Use the known storybook style for a single subject-focused panel.",
                "template_decision": {
                    "selected_template_ids": [template.id],
                    "extract_new_template": False,
                    "new_template": None,
                },
                "prompts": [
                    {
                        "subject_text": "Hero portrait of a traveler crossing a glowing forest bridge at sunrise.",
                        "template_ids": ["invented-template"],
                        "size": "1024x1536",
                        "quality": "high",
                        "image_model": "gpt-image-1.5",
                    }
                ],
            },
            available_templates=[template],
        )
    except RouterValidationError as exc:
        assert "invented-template" in str(exc)
    else:  # pragma: no cover - explicit failure branch for clarity
        raise AssertionError("Expected RouterValidationError for an unknown template id")


def test_validate_router_plan_enforces_exact_image_count() -> None:
    template = make_template(
        "storybook-soft",
        name="Storybook Soft",
        tags=["storybook"],
        summary="Soft painterly storybook lighting.",
        created_at="2026-04-23T12:00:00Z",
    )

    try:
        validate_router_plan(
            {
                "router_model_chosen": "gpt-5.4-mini",
                "rationale": "Split the request into two subject-focused panels.",
                "template_decision": {
                    "selected_template_ids": [template.id],
                    "extract_new_template": False,
                    "new_template": None,
                },
                "prompts": [
                    {
                        "subject_text": "Panel one shows the hero landing in a moonlit clearing.",
                        "template_ids": [template.id],
                        "size": "1024x1536",
                        "quality": "high",
                        "image_model": "gpt-image-1.5",
                    },
                    {
                        "subject_text": "Panel two shows the hero facing a dragon across the clearing.",
                        "template_ids": [template.id],
                        "size": "1024x1536",
                        "quality": "high",
                        "image_model": "gpt-image-1.5",
                    },
                ],
            },
            available_templates=[template],
            exact_image_count=1,
        )
    except RouterValidationError as exc:
        assert "exact_image_count" in str(exc)
    else:  # pragma: no cover - explicit failure branch for clarity
        raise AssertionError("Expected RouterValidationError for an exact-image-count mismatch")


def test_select_templates_for_router_prefilters_by_overlap_and_tiebreaks() -> None:
    templates = [
        make_template(
            "forest-hero-top",
            name="Forest Hero",
            tags=["forest", "hero"],
            summary="Forest hero adventure scene.",
            created_at="2026-04-23T12:00:00Z",
        ),
        make_template(
            "forest-only-newer",
            name="Forest Glow",
            tags=["forest"],
            summary="Forest atmosphere with glowing mist.",
            created_at="2026-04-23T11:00:00Z",
        ),
        make_template(
            "forest-only-older",
            name="Forest Echo",
            tags=["forest"],
            summary="Forest atmosphere with drifting leaves.",
            created_at="2026-04-23T10:00:00Z",
        ),
    ]
    templates.extend(
        make_template(
            f"filler-{index:02d}",
            name=f"Filler {index:02d}",
            tags=["unused"],
            summary="No lexical overlap with the chosen prompt.",
            created_at=f"2026-04-22T{index % 10:02d}:00:00Z",
        )
        for index in range(29)
    )

    selected = select_templates_for_router(
        user_prompt="A forest hero stands in glowing fog.",
        templates=templates,
    )

    assert len(selected) == 15
    assert [template.id for template in selected[:3]] == [
        "forest-hero-top",
        "forest-only-newer",
        "forest-only-older",
    ]


def test_select_templates_for_router_uses_newest_templates_when_all_scores_are_zero() -> None:
    templates = [
        make_template(
            f"template-{index:02d}",
            name=f"Template {index:02d}",
            tags=["archive"],
            summary="Library entry without prompt overlap.",
            created_at=f"2026-04-{30 - index:02d}T12:00:00Z",
        )
        for index in range(31)
    ]

    selected = select_templates_for_router(
        user_prompt="spaceship nebula cyberpunk skyline",
        templates=templates,
    )

    assert [template.id for template in selected] == [f"template-{index:02d}" for index in range(15)]
