from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pipelines.shared.db import ComicBookDB
from pipelines.workflows.template_upload.graph import run_upload_workflow

from .support import FakeRouterTransport
from .support import db
from .support import make_backfill_response
from .support import make_deps


def test_run_upload_workflow_happy_path_backfills_persists_and_finalizes(tmp_path: Path, db: ComicBookDB) -> None:
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
            "allow_external_path": True,
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
            "allow_external_path": True,
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
            "allow_external_path": True,
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
