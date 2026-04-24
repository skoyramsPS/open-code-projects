from __future__ import annotations

from types import SimpleNamespace


def make_deps(*, max_rows_per_file: int = 1000) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            comicbook_import_max_rows_per_file=max_rows_per_file,
        )
    )


def test_upload_parse_and_validate_preserves_empty_tags_without_backfill() -> None:
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
        make_deps(),
    )

    parsed_row = delta["parsed_rows"][0]
    assert parsed_row["template_id"] == "storybook-soft"
    assert parsed_row["tags"] == []
    assert parsed_row["needs_backfill_tags"] is False
    assert parsed_row["needs_backfill_summary"] is False
    assert parsed_row["validation_errors"] == []


def test_upload_parse_and_validate_ignores_created_by_run_with_warning() -> None:
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
        make_deps(),
    )

    parsed_row = delta["parsed_rows"][0]
    assert parsed_row["validation_errors"] == []
    assert "ignored_field_override:created_by_run" in parsed_row["warnings"]


def test_upload_parse_and_validate_marks_missing_required_fields_per_row() -> None:
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
        make_deps(),
    )

    parsed_row = delta["parsed_rows"][0]
    assert parsed_row["template_id"] == "storybook-soft"
    assert parsed_row["validation_errors"] == ["missing_required_field:name"]


def test_upload_parse_and_validate_rejects_files_over_row_limit() -> None:
    from comicbook.nodes.upload_parse_and_validate import upload_parse_and_validate

    try:
        upload_parse_and_validate(
            {
                "raw_rows": [
                    {"template_id": "row-1", "name": "One", "style_text": "alpha"},
                    {"template_id": "row-2", "name": "Two", "style_text": "beta"},
                ]
            },
            make_deps(max_rows_per_file=1),
        )
    except ValueError as exc:
        assert "max rows" in str(exc).lower()
    else:  # pragma: no cover - defensive assertion style for message check
        raise AssertionError("Expected upload_parse_and_validate to reject oversized files")
