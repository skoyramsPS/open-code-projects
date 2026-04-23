from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pytest

from comicbook.config import AppConfig
from comicbook.db import ComicBookDB, TemplateRecord
from comicbook.deps import Deps
from comicbook.state import RouterPlan, TemplateSummary


@pytest.fixture
def db(tmp_path: Path) -> ComicBookDB:
    database = ComicBookDB.connect(tmp_path / "comicbook.sqlite")
    try:
        yield database
    finally:
        database.close()


def make_template_record(
    template_id: str,
    *,
    name: str,
    style_text: str,
    tags: list[str],
    summary: str,
    created_at: str,
    created_by_run: str | None = None,
) -> TemplateRecord:
    return TemplateRecord(
        id=template_id,
        name=name,
        style_text=style_text,
        style_text_hash="hash-not-needed-for-test",
        tags=tags,
        summary=summary,
        supersedes_id=None,
        created_at=created_at,
        created_by_run=created_by_run,
    )


def to_summary(record: TemplateRecord) -> TemplateSummary:
    return TemplateSummary.model_validate(
        {
            "id": record.id,
            "name": record.name,
            "tags": record.tags,
            "summary": record.summary,
            "created_at": record.created_at,
        }
    )


def make_plan(*, extract_new_template: bool, new_template: dict | None, prompt_template_ids: list[str]) -> RouterPlan:
    return RouterPlan.model_validate(
        {
            "router_model_chosen": "gpt-5.4-mini",
            "rationale": "Compose deterministic prompts from stored style templates.",
            "template_decision": {
                "selected_template_ids": [template_id for template_id in prompt_template_ids if template_id != "new-template"],
                "extract_new_template": extract_new_template,
                "new_template": new_template,
            },
            "prompts": [
                {
                    "subject_text": "Traveler walking through a lantern-lit alley.",
                    "template_ids": prompt_template_ids,
                    "size": "1024x1536",
                    "quality": "high",
                    "image_model": "gpt-image-1.5",
                }
            ],
        }
    )


def make_deps(tmp_path: Path, db: ComicBookDB) -> Deps:
    config = AppConfig.model_validate(
        {
            "azure_openai_endpoint": "https://example.openai.azure.com",
            "azure_openai_api_key": "test-key",
            "azure_openai_api_version": "2025-04-01-preview",
            "azure_openai_chat_deployment": "gpt-5-router",
            "azure_openai_image_deployment": "gpt-image-1.5",
        }
    )
    return Deps(
        config=config,
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "run-1",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"image": {}},
        logger=logging.getLogger("test-fingerprint"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
    )


def test_compute_prompt_fingerprint_is_deterministic() -> None:
    from comicbook.fingerprint import compute_prompt_fingerprint

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


@pytest.mark.parametrize(
    ("rendered_prompt", "size", "quality", "image_model"),
    [
        ("Different prompt text", "1024x1536", "high", "gpt-image-1.5"),
        ("Soft painterly linework.\n\n---\n\nTraveler portrait at sunrise.", "1024x1024", "high", "gpt-image-1.5"),
        ("Soft painterly linework.\n\n---\n\nTraveler portrait at sunrise.", "1024x1536", "medium", "gpt-image-1.5"),
        ("Soft painterly linework.\n\n---\n\nTraveler portrait at sunrise.", "1024x1536", "high", "gpt-image-1"),
    ],
)
def test_compute_prompt_fingerprint_changes_when_any_render_input_changes(
    rendered_prompt: str,
    size: str,
    quality: str,
    image_model: str,
) -> None:
    from comicbook.fingerprint import compute_prompt_fingerprint

    original = compute_prompt_fingerprint(
        "Soft painterly linework.\n\n---\n\nTraveler portrait at sunrise.",
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
    )

    changed = compute_prompt_fingerprint(
        rendered_prompt,
        size=size,
        quality=quality,
        image_model=image_model,
    )

    assert changed != original


def test_materialize_rendered_prompts_preserves_prompt_and_template_order() -> None:
    from comicbook.fingerprint import materialize_rendered_prompts

    storybook = make_template_record(
        "storybook-soft",
        name="Storybook Soft",
        style_text="Soft painterly linework and warm golden light.",
        tags=["storybook", "warm"],
        summary="Warm painterly storybook finish.",
        created_at="2026-04-23T12:00:00Z",
    )
    ink = make_template_record(
        "inked-contrast",
        name="Inked Contrast",
        style_text="Bold black inks with crisp silhouette contrast.",
        tags=["ink", "contrast"],
        summary="High-contrast comic inking.",
        created_at="2026-04-23T12:05:00Z",
    )
    plan = RouterPlan.model_validate(
        {
            "router_model_chosen": "gpt-5.4-mini",
            "rationale": "Use two templates for the first prompt and none for the second.",
            "template_decision": {
                "selected_template_ids": [storybook.id, ink.id],
                "extract_new_template": False,
                "new_template": None,
            },
            "prompts": [
                {
                    "subject_text": "Traveler standing at the alley entrance.",
                    "template_ids": [storybook.id, ink.id],
                    "size": "1024x1536",
                    "quality": "high",
                    "image_model": "gpt-image-1.5",
                },
                {
                    "subject_text": "Lantern close-up with drifting fog.",
                    "template_ids": [],
                    "size": "1024x1024",
                    "quality": "medium",
                    "image_model": "gpt-image-1.5",
                },
            ],
        }
    )

    rendered_prompts = materialize_rendered_prompts(
        plan=plan,
        template_lookup={storybook.id: storybook, ink.id: ink},
    )

    assert [item.subject_text for item in rendered_prompts] == [
        "Traveler standing at the alley entrance.",
        "Lantern close-up with drifting fog.",
    ]
    assert rendered_prompts[0].rendered_prompt == (
        "Soft painterly linework and warm golden light.\n\n"
        "Bold black inks with crisp silhouette contrast.\n\n"
        "---\n\n"
        "Traveler standing at the alley entrance."
    )
    assert rendered_prompts[1].rendered_prompt == "Lantern close-up with drifting fog."


def test_persist_template_inserts_extracted_template_before_prompt_materialization(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.fingerprint import materialize_rendered_prompts
    from comicbook.nodes.persist_template import persist_template

    existing = db.insert_template(
        template_id="storybook-soft",
        name="Storybook Soft",
        style_text="Soft painterly linework and warm golden light.",
        tags=["storybook", "warm"],
        summary="Warm painterly storybook finish.",
        created_at="2026-04-23T11:55:00Z",
        created_by_run="seed-run",
    )
    plan = make_plan(
        extract_new_template=True,
        new_template={
            "id": "new-template",
            "name": "Neon Nights",
            "style_text": "Neon rim lighting and rainy night reflections.",
            "tags": ["neon", "night"],
            "summary": "Neon-lit rainy-night comic finish.",
        },
        prompt_template_ids=[existing.id, "new-template"],
    )

    delta = persist_template(
        {
            "run_id": "run-1",
            "templates": [to_summary(existing)],
            "plan": plan,
        },
        make_deps(tmp_path, db),
    )

    updated_plan = delta["plan"]
    updated_templates = delta["templates"]
    inserted_new_template = db.get_templates_by_ids(["new-template"])
    rendered_prompts = materialize_rendered_prompts(
        plan=updated_plan,
        template_lookup={record.id: record for record in db.get_templates_by_ids(updated_plan.prompts[0].template_ids)},
    )

    assert [template.id for template in updated_templates] == [existing.id, "new-template"]
    assert inserted_new_template[0].created_by_run == "run-1"
    assert updated_plan.prompts[0].template_ids == [existing.id, "new-template"]
    assert rendered_prompts[0].rendered_prompt == (
        "Soft painterly linework and warm golden light.\n\n"
        "Neon rim lighting and rainy night reflections.\n\n"
        "---\n\n"
        "Traveler walking through a lantern-lit alley."
    )


def test_persist_template_reuses_existing_duplicate_and_normalizes_prompt_ids(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.nodes.persist_template import persist_template

    existing = db.insert_template(
        template_id="sunlit-portrait",
        name="Sunlit Portrait",
        style_text="Warm portrait framing with bright painterly highlights.",
        tags=["portrait", "warm"],
        summary="Bright warm portrait finish.",
        created_at="2026-04-23T11:50:00Z",
        created_by_run="seed-run",
    )
    duplicate_plan = make_plan(
        extract_new_template=True,
        new_template={
            "id": "new-template",
            "name": "Sunlit Portrait",
            "style_text": "Warm portrait framing with bright painterly highlights.",
            "tags": ["portrait", "warm"],
            "summary": "Bright warm portrait finish.",
        },
        prompt_template_ids=["new-template"],
    )

    delta = persist_template(
        {
            "run_id": "run-2",
            "templates": [to_summary(existing)],
            "plan": duplicate_plan,
        },
        make_deps(tmp_path, db),
    )

    updated_plan = delta["plan"]
    updated_templates = delta["templates"]

    assert [template.id for template in updated_templates] == [existing.id]
    assert updated_plan.template_decision.new_template is not None
    assert updated_plan.template_decision.new_template.id == existing.id
    assert updated_plan.prompts[0].template_ids == [existing.id]


def test_persist_template_noops_when_router_did_not_extract_template(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.nodes.persist_template import persist_template

    plan = make_plan(
        extract_new_template=False,
        new_template=None,
        prompt_template_ids=[],
    )

    delta = persist_template(
        {
            "run_id": "run-3",
            "templates": [],
            "plan": plan,
        },
        make_deps(tmp_path, db),
    )

    assert delta == {}
