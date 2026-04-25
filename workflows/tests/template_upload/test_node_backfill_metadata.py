from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


@dataclass
class FakeRouterTransport:
    responses: list[object]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, *, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        if not self.responses:
            raise AssertionError("No fake router responses remain")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_response(*, payload: dict[str, Any], input_tokens: int = 120, output_tokens: int = 30) -> dict[str, Any]:
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(payload),
                    }
                ],
            }
        ],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


def make_deps(transport: FakeRouterTransport, *, pricing: dict[str, Any] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            azure_openai_endpoint="https://example.openai.azure.com",
            azure_openai_api_key=SimpleNamespace(get_secret_value=lambda: "test-key"),
            azure_openai_api_version="2025-04-01-preview",
            comicbook_import_backfill_model="gpt-5.4-mini",
        ),
        router_transport=transport,
        http_client=object(),
        pricing=pricing or {},
    )


def make_row(
    *,
    row_index: int,
    template_id: str,
    name: str = "Storybook Soft",
    style_text: str = "Soft painterly linework.",
    tags: list[str] | None = None,
    summary: str | None = None,
    needs_backfill_tags: bool = True,
    needs_backfill_summary: bool = True,
) -> dict[str, Any]:
    return {
        "row_index": row_index,
        "template_id": template_id,
        "name": name,
        "style_text": style_text,
        "tags": tags,
        "summary": summary,
        "created_at": None,
        "requested_supersedes_id": None,
        "resolved_supersedes_id": None,
        "validation_errors": [],
        "warnings": [],
        "needs_backfill_tags": needs_backfill_tags,
        "needs_backfill_summary": needs_backfill_summary,
        "backfill_raw": None,
        "write_mode": "skip",
        "retry_count": 0,
    }


def test_target_tree_upload_backfill_metadata_fills_missing_fields_and_tracks_usage() -> None:
    from comicbook.nodes.upload_backfill_metadata import upload_backfill_metadata

    transport = FakeRouterTransport(
        responses=[
            make_response(
                payload={
                    "tags": ["storybook", "Warm", "painterly"],
                    "summary": "Soft painterly style with warm storybook lighting.",
                }
            )
        ]
    )
    deps = make_deps(
        transport,
        pricing={
            "router_models": {
                "gpt-5.4-mini": {
                    "usd_per_1k_input_tokens": 0.002,
                    "usd_per_1k_output_tokens": 0.004,
                }
            }
        },
    )

    delta = upload_backfill_metadata(
        {
            "parsed_rows": [make_row(row_index=0, template_id="storybook-soft")],
            "rows_to_process": [0],
            "row_results": [],
            "usage": {"estimated_cost_usd": 0.0},
        },
        deps,
    )

    parsed_row = delta["parsed_rows"][0]
    assert parsed_row["tags"] == ["storybook", "warm", "painterly"]
    assert parsed_row["summary"] == "Soft painterly style with warm storybook lighting."
    assert parsed_row["needs_backfill_tags"] is False
    assert parsed_row["needs_backfill_summary"] is False
    assert parsed_row["backfill_raw"] is not None
    assert delta["row_results"] == []
    assert delta["usage"].router_calls == 1
    assert delta["usage"].router_input_tokens == 120
    assert delta["usage"].router_output_tokens == 30
    assert delta["usage"].estimated_cost_usd == 0.00036


def test_target_tree_upload_backfill_metadata_retries_invalid_response_once_then_succeeds() -> None:
    from comicbook.nodes.upload_backfill_metadata import upload_backfill_metadata

    transport = FakeRouterTransport(
        responses=[
            make_response(payload={"tags": [], "summary": "short"}),
            make_response(
                payload={
                    "tags": ["storybook", "soft-light"],
                    "summary": "Painterly warmth with soft storybook-style lighting.",
                },
                input_tokens=80,
                output_tokens=20,
            ),
        ]
    )

    delta = upload_backfill_metadata(
        {
            "parsed_rows": [make_row(row_index=0, template_id="storybook-soft")],
            "rows_to_process": [0],
            "row_results": [],
            "usage": {},
        },
        make_deps(transport),
    )

    assert delta["parsed_rows"][0]["tags"] == ["storybook", "soft-light"]
    assert delta["usage"].router_calls == 2
    assert len(transport.calls) == 2


def test_target_tree_upload_backfill_metadata_marks_rows_failed_when_backfill_disabled() -> None:
    from comicbook.nodes.upload_backfill_metadata import upload_backfill_metadata

    transport = FakeRouterTransport(responses=[])

    delta = upload_backfill_metadata(
        {
            "parsed_rows": [make_row(row_index=0, template_id="storybook-soft")],
            "rows_to_process": [0],
            "row_results": [],
            "usage": {},
            "no_backfill": True,
            "allow_missing_optional": False,
        },
        make_deps(transport),
    )

    assert delta["row_results"] == [
        {
            "row_index": 0,
            "template_id": "storybook-soft",
            "status": "failed",
            "reason": "backfill_disabled",
            "warnings": [],
            "retry_count": 0,
        }
    ]
    assert transport.calls == []


def test_target_tree_upload_backfill_metadata_allows_missing_optional_when_backfill_disabled() -> None:
    from comicbook.nodes.upload_backfill_metadata import upload_backfill_metadata

    transport = FakeRouterTransport(responses=[])

    delta = upload_backfill_metadata(
        {
            "parsed_rows": [make_row(row_index=0, template_id="storybook-soft")],
            "rows_to_process": [0],
            "row_results": [],
            "usage": {},
            "no_backfill": True,
            "allow_missing_optional": True,
        },
        make_deps(transport),
    )

    assert delta["parsed_rows"][0]["tags"] == []
    assert delta["parsed_rows"][0]["summary"] == "Storybook Soft"
    assert delta["row_results"] == []
    assert transport.calls == []


def test_target_tree_upload_backfill_metadata_marks_budget_exceeded_before_transport_call() -> None:
    from comicbook.nodes.upload_backfill_metadata import upload_backfill_metadata

    transport = FakeRouterTransport(responses=[])
    deps = make_deps(
        transport,
        pricing={
            "router_models": {
                "gpt-5.4-mini": {
                    "usd_per_1k_input_tokens": 0.01,
                    "usd_per_1k_output_tokens": 0.02,
                }
            }
        },
    )

    delta = upload_backfill_metadata(
        {
            "parsed_rows": [make_row(row_index=0, template_id="storybook-soft")],
            "rows_to_process": [0],
            "row_results": [],
            "usage": {},
            "budget_usd": 0.0,
        },
        deps,
    )

    assert delta["row_results"][0]["reason"] == "budget_exceeded"
    assert transport.calls == []


def test_target_tree_upload_backfill_metadata_trips_short_circuit_after_two_transport_failures() -> None:
    from comicbook.nodes.upload_backfill_metadata import upload_backfill_metadata

    transport = FakeRouterTransport(
        responses=[
            RuntimeError("timeout one"),
            RuntimeError("timeout one retry"),
            RuntimeError("timeout two"),
            RuntimeError("timeout two retry"),
        ]
    )

    delta = upload_backfill_metadata(
        {
            "parsed_rows": [
                make_row(row_index=0, template_id="row-0"),
                make_row(row_index=1, template_id="row-1"),
                make_row(row_index=2, template_id="row-2"),
            ],
            "rows_to_process": [0, 1, 2],
            "row_results": [],
            "usage": {},
        },
        make_deps(transport),
    )

    assert len(transport.calls) == 4
    assert delta["row_results"][0]["reason"].startswith("metadata_backfill_failed:")
    assert delta["row_results"][1]["reason"].startswith("metadata_backfill_failed:")
    assert delta["row_results"][2]["reason"] == "metadata_backfill_short_circuit"
