from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any


@dataclass
class FakeDB:
    existing_templates: dict[str, dict[str, Any]]

    def get_template_by_id(self, template_id: str) -> dict[str, Any] | None:
        row = self.existing_templates.get(template_id)
        return dict(row) if row is not None else None


def test_upload_decide_write_mode_marks_validation_failures_as_skip() -> None:
    from comicbook.nodes.upload_decide_write_mode import upload_decide_write_mode

    delta = upload_decide_write_mode(
        {
            "parsed_rows": [
                {
                    "row_index": 0,
                    "template_id": "storybook-soft",
                    "validation_errors": ["missing_required_field:name"],
                    "warnings": [],
                }
            ],
            "rows_to_process": [0],
            "row_results": [],
        },
        SimpleNamespace(db=FakeDB(existing_templates={})),
    )

    assert delta["parsed_rows"][0]["write_mode"] == "skip"
    assert delta["deferred_rows"] == []


def test_upload_decide_write_mode_marks_existing_templates_as_update() -> None:
    from comicbook.nodes.upload_decide_write_mode import upload_decide_write_mode

    deps = SimpleNamespace(
        db=FakeDB(
            existing_templates={
                "storybook-soft": {
                    "id": "storybook-soft",
                    "name": "Storybook Soft",
                    "style_text": "Soft painterly linework.",
                    "tags": ["storybook"],
                    "summary": "Warm storybook lighting.",
                    "created_at": "2026-04-23T12:00:00Z",
                    "created_by_run": "workflow_import",
                    "supersedes_id": None,
                }
            }
        )
    )

    delta = upload_decide_write_mode(
        {
            "parsed_rows": [
                {
                    "row_index": 0,
                    "template_id": "storybook-soft",
                    "validation_errors": [],
                    "warnings": [],
                }
            ],
            "rows_to_process": [0],
            "row_results": [],
        },
        deps,
    )

    assert delta["parsed_rows"][0]["write_mode"] == "update"
    assert delta["parsed_rows"][0]["existing_record"]["id"] == "storybook-soft"


def test_upload_decide_write_mode_marks_missing_templates_as_insert() -> None:
    from comicbook.nodes.upload_decide_write_mode import upload_decide_write_mode

    delta = upload_decide_write_mode(
        {
            "parsed_rows": [
                {
                    "row_index": 0,
                    "template_id": "storybook-soft",
                    "validation_errors": [],
                    "warnings": [],
                }
            ],
            "rows_to_process": [0],
            "row_results": [],
        },
        SimpleNamespace(db=FakeDB(existing_templates={})),
    )

    assert delta["parsed_rows"][0]["write_mode"] == "insert"
    assert delta["deferred_rows"] == []


def test_upload_decide_write_mode_defers_unresolved_same_run_supersedes_target() -> None:
    from comicbook.nodes.upload_decide_write_mode import upload_decide_write_mode

    delta = upload_decide_write_mode(
        {
            "parsed_rows": [
                {
                    "row_index": 0,
                    "template_id": "storybook-soft-v2",
                    "requested_supersedes_id": "storybook-soft",
                    "resolved_supersedes_id": None,
                    "validation_errors": [],
                    "warnings": [],
                },
                {
                    "row_index": 1,
                    "template_id": "storybook-soft",
                    "validation_errors": [],
                    "warnings": [],
                },
            ],
            "rows_to_process": [0, 1],
            "row_results": [],
        },
        SimpleNamespace(db=FakeDB(existing_templates={})),
    )

    assert delta["parsed_rows"][0]["write_mode"] == "defer"
    assert delta["parsed_rows"][1]["write_mode"] == "insert"
    assert delta["deferred_rows"] == [0]
