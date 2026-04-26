from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pipelines.shared.config import AppConfig
from pipelines.shared.deps import Deps
from pipelines.workflows.image_prompt_gen.state import TemplateSummary


@dataclass
class FakeDB:
    templates: list[TemplateSummary]

    def list_template_summaries(self, *, summary_factory):
        return list(self.templates)


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


def make_deps(tmp_path: Path, templates: list[TemplateSummary]) -> Deps:
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
        db=FakeDB(templates=templates),
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "run-1",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"image": {}},
        logger=logging.getLogger("test-node-load-templates"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
    )


def test_target_tree_load_templates_wrapper_keeps_full_catalog_when_count_is_30_or_fewer(tmp_path: Path) -> None:
    from comicbook.nodes.load_templates import load_templates

    templates = [
        make_template(
            "storybook-soft",
            name="Storybook Soft",
            tags=["storybook", "warm"],
            summary="Soft painterly storybook lighting.",
            created_at="2026-04-23T12:00:00Z",
        ),
        make_template(
            "inked-noir",
            name="Inked Noir",
            tags=["noir", "ink"],
            summary="Bold inked contrast for moody scenes.",
            created_at="2026-04-22T12:00:00Z",
        ),
    ]

    delta = load_templates({"user_prompt": "Warm storybook hero portrait"}, make_deps(tmp_path, templates))

    assert delta["template_catalog_size"] == 2
    assert [template.id for template in delta["templates"]] == ["storybook-soft", "inked-noir"]
    assert [template.id for template in delta["templates_sent_to_router"]] == ["storybook-soft", "inked-noir"]


def test_target_tree_load_templates_wrapper_prefilters_large_catalog_before_router(tmp_path: Path) -> None:
    from comicbook.nodes.load_templates import load_templates

    templates = [
        make_template(
            "heroic-forest",
            name="Heroic Forest",
            tags=["hero", "forest"],
            summary="Heroic forest adventure lighting.",
            created_at="2026-04-23T12:00:00Z",
        )
    ]
    templates.extend(
        make_template(
            f"archive-{index:02d}",
            name=f"Archive {index:02d}",
            tags=["archive"],
            summary="No lexical overlap with the chosen prompt.",
            created_at=f"2026-04-22T{index % 10:02d}:00:00Z",
        )
        for index in range(30)
    )

    delta = load_templates({"user_prompt": "A heroic forest traveler at dawn"}, make_deps(tmp_path, templates))

    assert delta["template_catalog_size"] == 31
    assert len(delta["templates"]) == 31
    assert len(delta["templates_sent_to_router"]) == 15
    assert delta["templates_sent_to_router"][0].id == "heroic-forest"
