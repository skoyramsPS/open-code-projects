from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace


@dataclass
class FakeDB:
    prior_results: list[dict[str, object]]

    def get_terminal_row_results_by_hash(self, source_file_hash: str) -> list[dict[str, object]]:
        assert source_file_hash == "hash-123"
        return list(self.prior_results)


def test_upload_resume_filter_skips_only_prior_terminal_successes() -> None:
    from comicbook.nodes.upload_resume_filter import upload_resume_filter

    deps = SimpleNamespace(
        db=FakeDB(
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
