from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def make_load_file_deps(*, max_file_bytes: int = 5_000_000, allow_external_path: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            comicbook_import_max_file_bytes=max_file_bytes,
            comicbook_import_allow_external_path=allow_external_path,
        )
    )


def make_parse_deps(*, max_rows_per_file: int = 1000) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            comicbook_import_max_rows_per_file=max_rows_per_file,
        )
    )


@dataclass
class FakeResumeDB:
    prior_results: list[dict[str, object]]

    def get_terminal_row_results_by_hash(self, source_file_hash: str) -> list[dict[str, object]]:
        assert source_file_hash == "hash-123"
        return list(self.prior_results)


@dataclass
class FakeExistingTemplateDB:
    existing_templates: dict[str, dict[str, Any]]

    def get_template_by_id(self, template_id: str) -> dict[str, Any] | None:
        row = self.existing_templates.get(template_id)
        return dict(row) if row is not None else None


def test_target_tree_upload_load_file_accepts_bare_array_input(tmp_path: Path) -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    payload = [
        {
            "template_id": "storybook-soft",
            "name": "Storybook Soft",
            "style_text": "Soft painterly linework.",
            "tags": ["storybook"],
            "summary": "Warm storybook lighting.",
        }
    ]
    source_file = tmp_path / "templates.json"
    encoded = json.dumps(payload).encode("utf-8")
    source_file.write_bytes(encoded)

    delta = upload_load_file(
        {
            "source_file_path": str(source_file),
            "allow_external_path": True,
        },
        make_load_file_deps(),
    )

    assert delta["source_file_path"] == str(source_file.resolve())
    assert delta["source_label"] == str(source_file.resolve())
    assert delta["source_file_hash"] == hashlib.sha256(encoded).hexdigest()
    assert delta["input_version"] == 1
    assert delta["raw_rows"] == payload


def test_target_tree_upload_load_file_accepts_versioned_envelope_input(tmp_path: Path) -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    payload = {
        "version": 1,
        "templates": [
            {
                "template_id": "storybook-soft",
                "name": "Storybook Soft",
                "style_text": "Soft painterly linework.",
            }
        ],
    }
    source_file = tmp_path / "templates.json"
    source_file.write_text(json.dumps(payload), encoding="utf-8")

    delta = upload_load_file(
        {
            "source_file_path": str(source_file),
            "allow_external_path": True,
        },
        make_load_file_deps(),
    )

    assert delta["input_version"] == 1
    assert delta["raw_rows"] == payload["templates"]


def test_target_tree_upload_load_file_accepts_stdin_payload() -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    stdin_text = json.dumps(
        [
            {
                "template_id": "storybook-soft",
                "name": "Storybook Soft",
                "style_text": "Soft painterly linework.",
            }
        ]
    )

    delta = upload_load_file(
        {
            "stdin_text": stdin_text,
            "allow_external_path": False,
        },
        make_load_file_deps(),
    )

    assert delta["source_file_path"] is None
    assert delta["source_label"] == "<stdin>"
    assert delta["source_file_hash"] == hashlib.sha256(stdin_text.encode("utf-8")).hexdigest()
    assert delta["raw_rows"][0]["template_id"] == "storybook-soft"


def test_target_tree_upload_load_file_rejects_invalid_top_level_shape(tmp_path: Path) -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    source_file = tmp_path / "templates.json"
    source_file.write_text(json.dumps({"template_id": "not-an-array"}), encoding="utf-8")

    with pytest.raises(ValueError, match="top-level"):
        upload_load_file(
            {
                "source_file_path": str(source_file),
                "allow_external_path": True,
            },
            make_load_file_deps(),
        )


def test_target_tree_upload_load_file_rejects_external_path_when_disallowed(tmp_path: Path) -> None:
    from comicbook.nodes.upload_load_file import upload_load_file

    source_file = tmp_path / "templates.json"
    source_file.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the allowed tree"):
        upload_load_file(
            {
                "source_file_path": str(source_file),
                "allow_external_path": False,
            },
            make_load_file_deps(),
        )


def test_target_tree_upload_parse_and_validate_preserves_empty_tags_without_backfill() -> None:
    from comicbook.nodes.upload_parse_and_validate import upload_parse_and_validate

    delta = upload_parse_and_validate(
        {
            "raw_rows": [
                {
                    "template_id": "storybook-soft",
                    "name": "Storybook Soft",
                    "style_text": "Soft painterly linework.",
                    "tags": [],
                    "summary": "Warm storybook lighting.",
                }
            ]
        },
        make_parse_deps(),
    )

    parsed_row = delta["parsed_rows"][0]
    assert parsed_row["template_id"] == "storybook-soft"
    assert parsed_row["tags"] == []
    assert parsed_row["needs_backfill_tags"] is False
    assert parsed_row["needs_backfill_summary"] is False
    assert parsed_row["validation_errors"] == []


def test_target_tree_upload_parse_and_validate_ignores_created_by_run_with_warning() -> None:
    from comicbook.nodes.upload_parse_and_validate import upload_parse_and_validate

    delta = upload_parse_and_validate(
        {
            "raw_rows": [
                {
                    "template_id": "storybook-soft",
                    "name": "Storybook Soft",
                    "style_text": "Soft painterly linework.",
                    "created_by_run": "hand-authored",
                }
            ]
        },
        make_parse_deps(),
    )

    parsed_row = delta["parsed_rows"][0]
    assert parsed_row["validation_errors"] == []
    assert "ignored_field_override:created_by_run" in parsed_row["warnings"]


def test_target_tree_upload_parse_and_validate_marks_missing_required_fields_per_row() -> None:
    from comicbook.nodes.upload_parse_and_validate import upload_parse_and_validate

    delta = upload_parse_and_validate(
        {
            "raw_rows": [
                {
                    "template_id": "storybook-soft",
                    "style_text": "Soft painterly linework.",
                }
            ]
        },
        make_parse_deps(),
    )

    parsed_row = delta["parsed_rows"][0]
    assert parsed_row["template_id"] == "storybook-soft"
    assert parsed_row["validation_errors"] == ["missing_required_field:name"]


def test_target_tree_upload_parse_and_validate_rejects_files_over_row_limit() -> None:
    from comicbook.nodes.upload_parse_and_validate import upload_parse_and_validate

    with pytest.raises(ValueError, match="max rows"):
        upload_parse_and_validate(
            {
                "raw_rows": [
                    {"template_id": "row-1", "name": "One", "style_text": "alpha"},
                    {"template_id": "row-2", "name": "Two", "style_text": "beta"},
                ]
            },
            make_parse_deps(max_rows_per_file=1),
        )


def test_target_tree_upload_resume_filter_skips_only_prior_terminal_successes() -> None:
    from comicbook.nodes.upload_resume_filter import upload_resume_filter

    deps = SimpleNamespace(
        db=FakeResumeDB(
            prior_results=[
                {"row_index": 0, "status": "inserted", "retry_count": 0},
                {"row_index": 1, "status": "failed", "retry_count": 2},
                {"row_index": 2, "status": "skipped_duplicate", "retry_count": 1},
            ]
        )
    )

    delta = upload_resume_filter(
        {
            "source_file_hash": "hash-123",
            "parsed_rows": [
                {"row_index": 0, "template_id": "row-0", "validation_errors": [], "warnings": []},
                {"row_index": 1, "template_id": "row-1", "validation_errors": [], "warnings": []},
                {"row_index": 2, "template_id": "row-2", "validation_errors": [], "warnings": []},
            ],
            "row_results": [],
        },
        deps,
    )

    assert delta["rows_to_process"] == [1]
    assert delta["rows_skipped_by_resume"] == [0, 2]
    assert [row["retry_count"] for row in delta["parsed_rows"]] == [0, 2, 1]
    assert delta["row_results"] == [
        {"row_index": 0, "template_id": "row-0", "status": "skipped_resume", "reason": "resume_success"},
        {"row_index": 2, "template_id": "row-2", "status": "skipped_resume", "reason": "resume_success"},
    ]


def test_target_tree_upload_decide_write_mode_marks_validation_failures_as_skip() -> None:
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
        SimpleNamespace(db=FakeExistingTemplateDB(existing_templates={})),
    )

    assert delta["parsed_rows"][0]["write_mode"] == "skip"
    assert delta["deferred_rows"] == []


def test_target_tree_upload_decide_write_mode_marks_existing_templates_as_update() -> None:
    from comicbook.nodes.upload_decide_write_mode import upload_decide_write_mode

    deps = SimpleNamespace(
        db=FakeExistingTemplateDB(
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


def test_target_tree_upload_decide_write_mode_marks_missing_templates_as_insert() -> None:
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
        SimpleNamespace(db=FakeExistingTemplateDB(existing_templates={})),
    )

    assert delta["parsed_rows"][0]["write_mode"] == "insert"
    assert delta["deferred_rows"] == []


def test_target_tree_upload_decide_write_mode_defers_unresolved_same_run_supersedes_target() -> None:
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
        SimpleNamespace(db=FakeExistingTemplateDB(existing_templates={})),
    )

    assert delta["parsed_rows"][0]["write_mode"] == "defer"
    assert delta["parsed_rows"][1]["write_mode"] == "insert"
    assert delta["deferred_rows"] == [0]
