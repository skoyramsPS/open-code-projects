from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pytest

from pipelines.workflows.image_prompt_gen.state import RenderedPrompt, RouterPlan, TemplateSummary
from pipelines.shared.config import AppConfig
from pipelines.shared.db import ComicBookDB, TemplateRecord
from pipelines.shared.deps import Deps
from pipelines.shared.fingerprint import compute_prompt_fingerprint, render_prompt_text


@pytest.fixture
def db(tmp_path: Path) -> ComicBookDB:
    database = ComicBookDB.connect(tmp_path / "comicbook.sqlite")
    try:
        yield database
    finally:
        database.close()


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
        logger=logging.getLogger("test-node-cache-lookup"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
    )


def make_template_record(template_id: str, *, style_text: str) -> TemplateRecord:
    return TemplateRecord(
        id=template_id,
        name="Storybook Soft",
        style_text=style_text,
        style_text_hash="unused-test-hash",
        tags=["storybook", "warm"],
        summary="Warm painterly storybook finish.",
        supersedes_id=None,
        created_at="2026-04-23T11:55:00Z",
        created_by_run="seed-run",
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


def make_plan(*, prompts: list[dict[str, object]], selected_template_ids: list[str]) -> RouterPlan:
    return RouterPlan.model_validate(
        {
            "router_model_chosen": "gpt-5.4-mini",
            "rationale": "Partition cached prompts from prompts that still need generation.",
            "template_decision": {
                "selected_template_ids": selected_template_ids,
                "extract_new_template": False,
                "new_template": None,
            },
            "prompts": prompts,
        }
    )


def make_rendered_prompt(
    *,
    fingerprint: str,
    subject_text: str,
    template_ids: list[str],
    size: str,
    quality: str,
    image_model: str,
    rendered_prompt: str,
) -> RenderedPrompt:
    return RenderedPrompt.model_validate(
        {
            "fingerprint": fingerprint,
            "subject_text": subject_text,
            "template_ids": template_ids,
            "size": size,
            "quality": quality,
            "image_model": image_model,
            "rendered_prompt": rendered_prompt,
        }
    )


def test_target_tree_cache_lookup_wrapper_partitions_cache_hits_and_deduplicates_generation_queue(
    tmp_path: Path, db: ComicBookDB
) -> None:
    from pipelines.workflows.image_prompt_gen.nodes.cache_lookup import cache_lookup

    storybook = db.insert_template(
        template_id="storybook-soft",
        name="Storybook Soft",
        style_text="Soft painterly linework and warm golden light.",
        tags=["storybook", "warm"],
        summary="Warm painterly storybook finish.",
        created_at="2026-04-23T11:55:00Z",
        created_by_run="seed-run",
    )
    cached_rendered_prompt = render_prompt_text(
        "Traveler portrait at sunrise.",
        [make_template_record(storybook.id, style_text=storybook.style_text)],
    )
    cached_fingerprint = compute_prompt_fingerprint(
        cached_rendered_prompt,
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
    )
    db.upsert_prompt_if_absent(
        prompt=make_rendered_prompt(
            fingerprint=cached_fingerprint,
            subject_text="Traveler portrait at sunrise.",
            template_ids=[storybook.id],
            size="1024x1536",
            quality="high",
            image_model="gpt-image-1.5",
            rendered_prompt=cached_rendered_prompt,
        ),
        first_seen_run="seed-run",
        created_at="2026-04-23T11:56:00Z",
    )
    db.insert_image_result(
        fingerprint=cached_fingerprint,
        run_id="seed-run",
        created_at="2026-04-23T11:57:00Z",
        status="generated",
        file_path="image_output/seed-run/cache-hit.png",
        bytes_written=128,
    )
    plan = make_plan(
        selected_template_ids=[storybook.id],
        prompts=[
            {
                "subject_text": "Traveler portrait at sunrise.",
                "template_ids": [storybook.id],
                "size": "1024x1536",
                "quality": "high",
                "image_model": "gpt-image-1.5",
            },
            {
                "subject_text": "Traveler portrait at sunrise.",
                "template_ids": [storybook.id],
                "size": "1024x1536",
                "quality": "high",
                "image_model": "gpt-image-1.5",
            },
            {
                "subject_text": "Lantern close-up in drifting fog.",
                "template_ids": [],
                "size": "1024x1024",
                "quality": "medium",
                "image_model": "gpt-image-1.5",
            },
        ],
    )

    delta = cache_lookup(
        {
            "run_id": "run-2",
            "started_at": "2026-04-23T12:00:00Z",
            "templates": [to_summary(storybook)],
            "plan": plan,
            "force_regenerate": False,
        },
        make_deps(tmp_path, db),
    )

    generated_fingerprints = [prompt.fingerprint for prompt in delta["to_generate"]]
    cache_hit_fingerprints = [prompt.fingerprint for prompt in delta["cache_hits"]]
    all_fingerprints = [prompt.fingerprint for prompt in delta["rendered_prompts"]]

    assert len(delta["rendered_prompts"]) == 3
    assert all_fingerprints[0] == all_fingerprints[1]
    assert list(delta["rendered_prompts_by_fp"]) == [cache_hit_fingerprints[0], generated_fingerprints[0]]
    assert cache_hit_fingerprints == [cached_fingerprint]
    assert generated_fingerprints == [all_fingerprints[2]]
    assert db.get_prompt_by_fingerprint(cached_fingerprint) is not None
    assert db.get_prompt_by_fingerprint(all_fingerprints[2]) is not None


def test_target_tree_cache_lookup_wrapper_force_regenerate_ignores_existing_successful_image(
    tmp_path: Path, db: ComicBookDB
) -> None:
    from pipelines.workflows.image_prompt_gen.nodes.cache_lookup import cache_lookup

    storybook = db.insert_template(
        template_id="storybook-soft",
        name="Storybook Soft",
        style_text="Soft painterly linework and warm golden light.",
        tags=["storybook", "warm"],
        summary="Warm painterly storybook finish.",
        created_at="2026-04-23T11:55:00Z",
        created_by_run="seed-run",
    )
    rendered_prompt = render_prompt_text(
        "Traveler portrait at sunrise.",
        [make_template_record(storybook.id, style_text=storybook.style_text)],
    )
    fingerprint = compute_prompt_fingerprint(
        rendered_prompt,
        size="1024x1536",
        quality="high",
        image_model="gpt-image-1.5",
    )
    db.upsert_prompt_if_absent(
        prompt=make_rendered_prompt(
            fingerprint=fingerprint,
            subject_text="Traveler portrait at sunrise.",
            template_ids=[storybook.id],
            size="1024x1536",
            quality="high",
            image_model="gpt-image-1.5",
            rendered_prompt=rendered_prompt,
        ),
        first_seen_run="seed-run",
        created_at="2026-04-23T11:56:00Z",
    )
    db.insert_image_result(
        fingerprint=fingerprint,
        run_id="seed-run",
        created_at="2026-04-23T11:57:00Z",
        status="generated",
        file_path="image_output/seed-run/cache-hit.png",
        bytes_written=128,
    )

    delta = cache_lookup(
        {
            "run_id": "run-2",
            "started_at": "2026-04-23T12:00:00Z",
            "templates": [to_summary(storybook)],
            "plan": make_plan(
                selected_template_ids=[storybook.id],
                prompts=[
                    {
                        "subject_text": "Traveler portrait at sunrise.",
                        "template_ids": [storybook.id],
                        "size": "1024x1536",
                        "quality": "high",
                        "image_model": "gpt-image-1.5",
                    }
                ],
            ),
            "force_regenerate": True,
        },
        make_deps(tmp_path, db),
    )

    assert delta["cache_hits"] == []
    assert [prompt.fingerprint for prompt in delta["to_generate"]] == [fingerprint]
    assert db.get_prompt_by_fingerprint(fingerprint).first_seen_run == "seed-run"


def test_target_tree_cache_lookup_wrapper_does_not_treat_failed_images_as_cache_hits(
    tmp_path: Path, db: ComicBookDB
) -> None:
    from pipelines.workflows.image_prompt_gen.nodes.cache_lookup import cache_lookup

    rendered_prompt = "Moody silhouette in heavy rain."
    fingerprint = compute_prompt_fingerprint(
        rendered_prompt,
        size="1024x1024",
        quality="medium",
        image_model="gpt-image-1.5",
    )
    db.upsert_prompt_if_absent(
        prompt=make_rendered_prompt(
            fingerprint=fingerprint,
            subject_text=rendered_prompt,
            template_ids=[],
            size="1024x1024",
            quality="medium",
            image_model="gpt-image-1.5",
            rendered_prompt=rendered_prompt,
        ),
        first_seen_run="seed-run",
        created_at="2026-04-23T11:56:00Z",
    )
    db.insert_image_result(
        fingerprint=fingerprint,
        run_id="seed-run",
        created_at="2026-04-23T11:57:00Z",
        status="failed",
        failure_reason="content_filter",
    )

    delta = cache_lookup(
        {
            "run_id": "run-2",
            "started_at": "2026-04-23T12:00:00Z",
            "templates": [],
            "plan": make_plan(
                selected_template_ids=[],
                prompts=[
                    {
                        "subject_text": rendered_prompt,
                        "template_ids": [],
                        "size": "1024x1024",
                        "quality": "medium",
                        "image_model": "gpt-image-1.5",
                    }
                ],
            ),
            "force_regenerate": False,
        },
        make_deps(tmp_path, db),
    )

    assert delta["cache_hits"] == []
    assert [prompt.fingerprint for prompt in delta["to_generate"]] == [fingerprint]
