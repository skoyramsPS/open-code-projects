from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from pipelines.workflows.image_prompt_gen.state import TemplateSummary
from pipelines.shared.config import AppConfig
from pipelines.shared.deps import Deps


@dataclass
class FakeRouterTransport:
    responses: list[dict[str, Any]]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, *, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("No fake router responses remain")
        return self.responses.pop(0)


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


def make_response(output_text: str, *, input_tokens: int = 0, output_tokens: int = 0) -> dict[str, Any]:
    return {
        "output": [{"type": "message", "content": [{"type": "output_text", "text": output_text}]}],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


def make_deps(tmp_path: Path, transport: FakeRouterTransport) -> Deps:
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
        db=object(),
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "run-1",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"image": {}},
        logger=logging.getLogger("test-node-router"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        router_transport=transport,
    )


def test_target_tree_router_wrapper_sends_expected_request_and_parses_valid_plan(tmp_path: Path) -> None:
    from comicbook.nodes.router import router

    template = make_template(
        "storybook-soft",
        name="Storybook Soft",
        tags=["storybook", "warm"],
        summary="Soft painterly storybook lighting.",
        created_at="2026-04-23T12:00:00Z",
    )
    transport = FakeRouterTransport(
        responses=[
            make_response(
                json.dumps(
                    {
                        "router_model_chosen": "gpt-5.4-mini",
                        "rationale": "One known template is enough for this single portrait request.",
                        "needs_escalation": False,
                        "escalation_reason": None,
                        "template_decision": {
                            "selected_template_ids": [template.id],
                            "extract_new_template": False,
                            "new_template": None,
                        },
                        "prompts": [
                            {
                                "subject_text": "Heroic portrait of a traveler at sunrise.",
                                "template_ids": [template.id],
                                "size": "1024x1536",
                                "quality": "high",
                                "image_model": "gpt-image-1.5",
                            }
                        ],
                    }
                ),
                input_tokens=120,
                output_tokens=45,
            )
        ]
    )

    delta = router(
        {
            "user_prompt": "Heroic portrait of a traveler at sunrise.",
            "templates_sent_to_router": [template],
            "exact_image_count": 1,
        },
        make_deps(tmp_path, transport),
    )

    assert delta["router_model"] == "gpt-5.4-mini"
    assert delta["plan_repair_attempts"] == 0
    assert delta["router_escalated"] is False
    assert delta["plan"].template_decision.selected_template_ids == [template.id]
    assert delta["usage"].router_calls == 1
    assert delta["usage"].router_input_tokens == 120
    assert delta["usage"].router_output_tokens == 45

    assert len(transport.calls) == 1
    first_call = transport.calls[0]
    assert first_call["url"] == "https://example.openai.azure.com/openai/responses?api-version=2025-04-01-preview"
    assert first_call["payload"]["model"] == "gpt-5.4-mini"
    assert first_call["payload"]["response_format"]["type"] == "json_schema"

    user_message = first_call["payload"]["input"][1]
    router_input = json.loads(user_message["content"])
    assert router_input["user_prompt"] == "Heroic portrait of a traveler at sunrise."
    assert router_input["constraints"]["exact_image_count"] == 1
    assert router_input["known_templates"] == [
        {
            "id": "storybook-soft",
            "name": "Storybook Soft",
            "tags": ["storybook", "warm"],
            "summary": "Soft painterly storybook lighting.",
        }
    ]


def test_target_tree_router_wrapper_repairs_invalid_first_response_once(tmp_path: Path) -> None:
    from comicbook.nodes.router import router

    template = make_template(
        "storybook-soft",
        name="Storybook Soft",
        tags=["storybook", "warm"],
        summary="Soft painterly storybook lighting.",
        created_at="2026-04-23T12:00:00Z",
    )
    transport = FakeRouterTransport(
        responses=[
            make_response(
                json.dumps(
                    {
                        "router_model_chosen": "gpt-5.4-mini",
                        "rationale": "Use a made-up template id.",
                        "needs_escalation": False,
                        "escalation_reason": None,
                        "template_decision": {
                            "selected_template_ids": [template.id],
                            "extract_new_template": False,
                            "new_template": None,
                        },
                        "prompts": [
                            {
                                "subject_text": "Heroic portrait of a traveler at sunrise.",
                                "template_ids": ["invented-template"],
                                "size": "1024x1536",
                                "quality": "high",
                                "image_model": "gpt-image-1.5",
                            }
                        ],
                    }
                ),
                input_tokens=100,
                output_tokens=20,
            ),
            make_response(
                json.dumps(
                    {
                        "router_model_chosen": "gpt-5.4-mini",
                        "rationale": "Repaired to use only known template ids.",
                        "needs_escalation": False,
                        "escalation_reason": None,
                        "template_decision": {
                            "selected_template_ids": [template.id],
                            "extract_new_template": False,
                            "new_template": None,
                        },
                        "prompts": [
                            {
                                "subject_text": "Heroic portrait of a traveler at sunrise.",
                                "template_ids": [template.id],
                                "size": "1024x1536",
                                "quality": "high",
                                "image_model": "gpt-image-1.5",
                            }
                        ],
                    }
                ),
                input_tokens=80,
                output_tokens=30,
            ),
        ]
    )

    delta = router(
        {
            "user_prompt": "Heroic portrait of a traveler at sunrise.",
            "templates_sent_to_router": [template],
        },
        make_deps(tmp_path, transport),
    )

    assert delta["plan_repair_attempts"] == 1
    assert delta["plan"].template_decision.selected_template_ids == [template.id]
    assert delta["usage"].router_calls == 2
    assert delta["usage"].router_input_tokens == 180
    assert delta["usage"].router_output_tokens == 50
    assert len(transport.calls) == 2
    assert transport.calls[0]["payload"]["model"] == "gpt-5.4-mini"
    assert transport.calls[1]["payload"]["model"] == "gpt-5.4-mini"
    assert "failed validation" in transport.calls[1]["payload"]["input"][1]["content"]
    assert "invented-template" in transport.calls[1]["payload"]["input"][1]["content"]


def test_target_tree_router_wrapper_escalates_to_stronger_model_when_requested(tmp_path: Path) -> None:
    from comicbook.nodes.router import router

    template = make_template(
        "storybook-soft",
        name="Storybook Soft",
        tags=["storybook", "warm"],
        summary="Soft painterly storybook lighting.",
        created_at="2026-04-23T12:00:00Z",
    )
    transport = FakeRouterTransport(
        responses=[
            make_response(
                json.dumps(
                    {
                        "router_model_chosen": "gpt-5.4-mini",
                        "rationale": "The request is ambiguous enough to benefit from the stronger router.",
                        "needs_escalation": True,
                        "escalation_reason": "Multiple style directions conflict.",
                        "template_decision": {
                            "selected_template_ids": [template.id],
                            "extract_new_template": False,
                            "new_template": None,
                        },
                        "prompts": [
                            {
                                "subject_text": "Traveler portrait in a glowing forest.",
                                "template_ids": [template.id],
                                "size": "1024x1536",
                                "quality": "high",
                                "image_model": "gpt-image-1.5",
                            }
                        ],
                    }
                ),
                input_tokens=90,
                output_tokens=25,
            ),
            make_response(
                json.dumps(
                    {
                        "router_model_chosen": "gpt-5.4",
                        "rationale": "The stronger model resolves the ambiguity into one final plan.",
                        "needs_escalation": False,
                        "escalation_reason": None,
                        "template_decision": {
                            "selected_template_ids": [template.id],
                            "extract_new_template": False,
                            "new_template": None,
                        },
                        "prompts": [
                            {
                                "subject_text": "Traveler portrait in a glowing forest with a clear storybook mood.",
                                "template_ids": [template.id],
                                "size": "1024x1536",
                                "quality": "high",
                                "image_model": "gpt-image-1.5",
                            }
                        ],
                    }
                ),
                input_tokens=140,
                output_tokens=40,
            ),
        ]
    )

    delta = router(
        {
            "user_prompt": "Traveler portrait in a glowing forest with mixed noir and storybook cues.",
            "templates_sent_to_router": [template],
        },
        make_deps(tmp_path, transport),
    )

    assert delta["router_escalated"] is True
    assert delta["router_model"] == "gpt-5.4"
    assert delta["plan"].router_model_chosen == "gpt-5.4"
    assert delta["plan"].needs_escalation is False
    assert delta["plan_repair_attempts"] == 0
    assert delta["usage"].router_calls == 2
    assert delta["usage"].router_input_tokens == 230
    assert delta["usage"].router_output_tokens == 65
    assert [call["payload"]["model"] for call in transport.calls] == ["gpt-5.4-mini", "gpt-5.4"]
