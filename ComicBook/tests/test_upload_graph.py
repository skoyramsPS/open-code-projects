from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from comicbook.config import AppConfig
from comicbook.db import ComicBookDB
from comicbook.deps import Deps


@dataclass
class FakeRouterTransport:
    responses: list[dict[str, Any]]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, *, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        self.calls.append({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        if not self.responses:
            raise AssertionError("No fake router responses remain")
        return self.responses.pop(0)


@pytest.fixture
def db(tmp_path: Path) -> ComicBookDB:
    database = ComicBookDB.connect(tmp_path / "comicbook.sqlite")
    try:
        yield database
    finally:
        database.close()


def make_config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "azure_openai_endpoint": "https://example.openai.azure.com",
            "azure_openai_api_key": "test-key",
            "azure_openai_api_version": "2025-04-01-preview",
            "azure_openai_chat_deployment": "gpt-5-router",
            "azure_openai_image_deployment": "gpt-image-1.5",
        }
    )


def make_deps(tmp_path: Path, db: ComicBookDB, *, router_transport: FakeRouterTransport | None = None) -> Deps:
    return Deps(
        config=make_config(),
        db=db,
        http_client=object(),
        clock=lambda: datetime(2026, 4, 23, 12, 0, 0),
        uuid_factory=lambda: "generated-import-run-id",
        output_dir=tmp_path / "image_output",
        runs_dir=tmp_path / "runs",
        logs_dir=tmp_path / "logs",
        pricing={"router_models": {"gpt-5.4-mini": {"usd_per_1k_input_tokens": 0.002, "usd_per_1k_output_tokens": 0.004}}},
        logger=logging.getLogger("test-upload-graph"),
        pid_provider=lambda: 123,
        hostname_provider=lambda: "host-a",
        router_transport=router_transport,
    )


def make_backfill_response() -> dict[str, Any]:
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "tags": ["storybook", "warm", "painterly"],
                                "summary": "Soft painterly style with warm storybook lighting.",
                            }
                        ),
                    }
                ],
            }
        ],
        "usage": {"input_tokens": 120, "output_tokens": 30},
    }


def test_run_upload_workflow_happy_path_backfills_persists_and_finalizes(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.upload_graph import run_upload_workflow

    payload = [
        {
            "template_id": "storybook-soft",
            "name": "Storybook Soft",
            "style_text": "Soft painterly linework.",
        }
    ]
    source_file = tmp_path / "templates.json"
    encoded = json.dumps(payload).encode("utf-8")
    source_file.write_bytes(encoded)

    import_run = db.acquire_import_lock(
        import_run_id="import-run-1",
        source_file_path=str(source_file),
        source_file_hash=hashlib.sha256(encoded).hexdigest(),
        started_at="2026-04-23T12:00:00Z",
        dry_run=False,
        pid=123,
        host="host-a",
        pid_is_alive=lambda pid: True,
    )

    final_state = run_upload_workflow(
        {
            "import_run_id": import_run.import_run_id,
            "source_file_path": str(source_file),
            "allow_external_path": False,
            "dry_run": False,
            "no_backfill": False,
            "allow_missing_optional": False,
            "budget_usd": None,
            "redact_style_text_in_logs": False,
            "started_at": import_run.started_at,
            "row_results": [],
            "errors": [],
            "usage": {},
        },
        make_deps(tmp_path, db, router_transport=FakeRouterTransport(responses=[make_backfill_response()])),
    )

    assert final_state["run_status"] == "succeeded"
    assert final_state["row_results"][0]["status"] == "inserted"
    assert db.get_template_by_id("storybook-soft") is not None

    import_record = db.get_import_run("import-run-1")
    assert import_record is not None
    assert import_record.status == "succeeded"
    assert import_record.inserted == 1
    assert import_record.backfilled == 1

    report_path = tmp_path / "runs" / "import-run-1" / "import_report.md"
    log_path = tmp_path / "logs" / "import-run-1.import.jsonl"
    assert report_path.exists()
    assert log_path.exists()


def test_run_upload_workflow_partial_success_records_failed_rows(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.upload_graph import run_upload_workflow

    payload = [
        {
            "template_id": "good-row",
            "name": "Good Row",
            "style_text": "Clean painted linework.",
            "tags": ["painted"],
            "summary": "Painterly style.",
        },
        {
            "template_id": "bad-row",
            "style_text": "Missing name should fail.",
            "tags": ["broken"],
            "summary": "Broken style row.",
        },
    ]
    source_file = tmp_path / "templates.json"
    encoded = json.dumps(payload).encode("utf-8")
    source_file.write_bytes(encoded)

    import_run = db.acquire_import_lock(
        import_run_id="import-run-2",
        source_file_path=str(source_file),
        source_file_hash=hashlib.sha256(encoded).hexdigest(),
        started_at="2026-04-23T12:00:00Z",
        dry_run=False,
        pid=123,
        host="host-a",
        pid_is_alive=lambda pid: True,
    )

    final_state = run_upload_workflow(
        {
            "import_run_id": import_run.import_run_id,
            "source_file_path": str(source_file),
            "allow_external_path": False,
            "dry_run": False,
            "no_backfill": False,
            "allow_missing_optional": False,
            "budget_usd": None,
            "redact_style_text_in_logs": False,
            "started_at": import_run.started_at,
            "row_results": [],
            "errors": [],
            "usage": {},
        },
        make_deps(tmp_path, db),
    )

    assert final_state["run_status"] == "partial"
    assert [result["status"] for result in final_state["row_results"]] == ["inserted", "failed"]

    import_record = db.get_import_run("import-run-2")
    assert import_record is not None
    assert import_record.status == "partial"
    assert import_record.inserted == 1
    assert import_record.failed == 1


def test_run_upload_workflow_dry_run_writes_report_without_template_changes(tmp_path: Path, db: ComicBookDB) -> None:
    from comicbook.upload_graph import run_upload_workflow

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

    import_run = db.acquire_import_lock(
        import_run_id="import-run-3",
        source_file_path=str(source_file),
        source_file_hash=hashlib.sha256(encoded).hexdigest(),
        started_at="2026-04-23T12:00:00Z",
        dry_run=True,
        pid=123,
        host="host-a",
        pid_is_alive=lambda pid: True,
    )

    final_state = run_upload_workflow(
        {
            "import_run_id": import_run.import_run_id,
            "source_file_path": str(source_file),
            "allow_external_path": False,
            "dry_run": True,
            "no_backfill": False,
            "allow_missing_optional": False,
            "budget_usd": None,
            "redact_style_text_in_logs": False,
            "started_at": import_run.started_at,
            "row_results": [],
            "errors": [],
            "usage": {},
        },
        make_deps(tmp_path, db),
    )

    assert final_state["run_status"] == "dry_run"
    assert final_state["row_results"][0]["status"] == "dry_run_ok"
    assert db.get_template_by_id("storybook-soft") is None

    import_record = db.get_import_run("import-run-3")
    assert import_record is not None
    assert import_record.status == "dry_run"
    assert (tmp_path / "runs" / "import-run-3" / "import_report.md").exists()
