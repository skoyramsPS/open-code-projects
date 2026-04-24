from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


@dataclass
class FakeDB:
    existing_template: dict[str, Any] | None = None
    inserted_calls: list[dict[str, Any]] = field(default_factory=list)
    updated_calls: list[dict[str, Any]] = field(default_factory=list)
    row_result_calls: list[dict[str, Any]] = field(default_factory=list)

    def get_template_by_id(self, template_id: str) -> dict[str, Any] | None:
        if self.existing_template is not None and self.existing_template["id"] == template_id:
            return dict(self.existing_template)
        return None

    def insert_template(self, **kwargs: Any) -> dict[str, Any]:
        self.inserted_calls.append(dict(kwargs))
        return {
            "id": kwargs["template_id"],
            "name": kwargs["name"],
            "style_text": kwargs["style_text"],
            "tags": kwargs["tags"],
            "summary": kwargs["summary"],
            "created_at": kwargs["created_at"],
            "created_by_run": kwargs["created_by_run"],
            "supersedes_id": kwargs.get("supersedes_id"),
        }

    def update_template_in_place(self, **kwargs: Any) -> dict[str, Any]:
        self.updated_calls.append(dict(kwargs))
        return dict(kwargs)

    def record_import_row_result(self, **kwargs: Any) -> None:
        self.row_result_calls.append(dict(kwargs))


def test_upload_persist_turns_zero_diff_update_into_skipped_duplicate() -> None:
    from comicbook.nodes.upload_persist import upload_persist

    deps = SimpleNamespace(
        db=FakeDB(
            existing_template={
                "id": "storybook-soft",
                "name": "Storybook Soft",
                "style_text": "Soft painterly linework.",
                "tags": ["storybook"],
                "summary": "Warm storybook lighting.",
                "created_at": "2026-04-23T12:00:00Z",
                "created_by_run": "workflow_import",
                "supersedes_id": None,
            }
        )
    )

    delta = upload_persist(
        {
            "import_run_id": "import-run-1",
            "source_file_hash": "hash-123",
            "dry_run": False,
            "row_results": [],
            "parsed_rows": [
                {
                    "row_index": 0,
                    "template_id": "storybook-soft",
                    "name": "Storybook Soft",
                    "style_text": "Soft painterly linework.",
                    "tags": ["storybook"],
                    "summary": "Warm storybook lighting.",
                    "created_at": "2026-04-23T12:00:00Z",
                    "requested_supersedes_id": None,
                    "resolved_supersedes_id": None,
                    "warnings": [],
                    "validation_errors": [],
                    "write_mode": "update",
                    "retry_count": 0,
                }
            ],
            "rows_to_process": [0],
        },
        deps,
    )

    assert deps.db.updated_calls == []
    assert deps.db.row_result_calls[0]["status"] == "skipped_duplicate"
    assert delta["row_results"][0]["status"] == "skipped_duplicate"


def test_upload_persist_nulls_unresolved_supersedes_id_and_keeps_warning() -> None:
    from comicbook.nodes.upload_persist import upload_persist

    deps = SimpleNamespace(db=FakeDB())

    delta = upload_persist(
        {
            "import_run_id": "import-run-1",
            "source_file_hash": "hash-123",
            "dry_run": False,
            "row_results": [],
            "parsed_rows": [
                {
                    "row_index": 0,
                    "template_id": "storybook-soft",
                    "name": "Storybook Soft",
                    "style_text": "Soft painterly linework.",
                    "tags": ["storybook"],
                    "summary": "Warm storybook lighting.",
                    "created_at": "2026-04-23T12:00:00Z",
                    "requested_supersedes_id": "missing-template",
                    "resolved_supersedes_id": None,
                    "warnings": ["missing_supersedes_target:missing-template"],
                    "validation_errors": [],
                    "write_mode": "insert",
                    "retry_count": 0,
                }
            ],
            "rows_to_process": [0],
        },
        deps,
    )

    assert deps.db.inserted_calls[0]["supersedes_id"] is None
    assert deps.db.row_result_calls[0]["persisted_supersedes_id"] is None
    assert "missing_supersedes_target:missing-template" in delta["row_results"][0]["warnings"]
