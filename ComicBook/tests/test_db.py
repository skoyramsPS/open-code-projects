from __future__ import annotations

from pathlib import Path

import pytest

from comicbook.db import ComicBookDB, RunLockError
from comicbook.state import RenderedPrompt


@pytest.fixture
def db(tmp_path: Path) -> ComicBookDB:
    database = ComicBookDB.connect(tmp_path / "comicbook.sqlite")
    try:
        yield database
    finally:
        database.close()


def test_initialize_is_idempotent_and_enables_wal(db: ComicBookDB) -> None:
    db.initialize()
    db.initialize()

    objects = db.connection.execute(
        "SELECT type, name FROM sqlite_master WHERE name IN (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ORDER BY name",
        (
            "daily_run_rollup",
            "images",
            "import_row_results",
            "import_runs",
            "ix_import_row_results_hash_row",
            "ix_import_row_results_template",
            "ix_import_runs_status",
            "prompts",
            "runs",
            "templates",
        ),
    ).fetchall()
    journal_mode = db.connection.execute("PRAGMA journal_mode").fetchone()[0]

    assert [(row["type"], row["name"]) for row in objects] == [
        ("view", "daily_run_rollup"),
        ("table", "images"),
        ("table", "import_row_results"),
        ("table", "import_runs"),
        ("index", "ix_import_row_results_hash_row"),
        ("index", "ix_import_row_results_template"),
        ("index", "ix_import_runs_status"),
        ("table", "prompts"),
        ("table", "runs"),
        ("table", "templates"),
    ]
    assert journal_mode.lower() == "wal"


def test_import_lock_blocks_second_active_import_until_release(db: ComicBookDB) -> None:
    db.acquire_import_lock(
        import_run_id="import-run-1",
        source_file_path="templates.json",
        source_file_hash="hash-123",
        started_at="2026-04-23T12:00:00Z",
        dry_run=False,
        pid=101,
        host="host-a",
        pid_is_alive=lambda pid: True,
    )

    with pytest.raises(RunLockError):
        db.acquire_import_lock(
            import_run_id="import-run-2",
            source_file_path="templates.json",
            source_file_hash="hash-456",
            started_at="2026-04-23T12:01:00Z",
            dry_run=False,
            pid=202,
            host="host-a",
            pid_is_alive=lambda pid: True,
        )

    db.release_import_lock("import-run-1")

    acquired = db.acquire_import_lock(
        import_run_id="import-run-2",
        source_file_path="templates.json",
        source_file_hash="hash-456",
        started_at="2026-04-23T12:01:00Z",
        dry_run=False,
        pid=202,
        host="host-a",
        pid_is_alive=lambda pid: True,
    )

    assert acquired.import_run_id == "import-run-2"
    assert acquired.status == "running"


def test_insert_template_deduplicates_and_supports_append_only_lineage(db: ComicBookDB) -> None:
    original = db.insert_template(
        template_id="storybook-soft",
        name="Storybook Soft",
        style_text="Soft painterly linework and warm lighting.",
        tags=["storybook", "warm"],
        summary="Soft painterly linework with warm light.",
        created_at="2026-04-23T12:00:00Z",
        created_by_run="run-1",
    )
    duplicate = db.insert_template(
        template_id="storybook-soft-duplicate",
        name="Storybook Soft",
        style_text="Soft painterly linework and warm lighting.",
        tags=["storybook", "warm"],
        summary="Duplicate text should be ignored.",
        created_at="2026-04-23T12:01:00Z",
        created_by_run="run-2",
    )
    revision = db.insert_template(
        template_id="storybook-soft-v2",
        name="Storybook Soft",
        style_text="Soft painterly linework, warm lighting, and richer ink texture.",
        tags=["storybook", "warm", "ink"],
        summary="Append-only revision with richer texture.",
        created_at="2026-04-23T12:02:00Z",
        created_by_run="run-3",
        supersedes_id=original.id,
    )

    summaries = db.list_template_summaries()
    full_rows = db.get_templates_by_ids([revision.id, original.id])

    assert duplicate.id == original.id
    assert len(summaries) == 2
    assert [summary.id for summary in summaries] == [revision.id, original.id]
    assert [row.id for row in full_rows] == [revision.id, original.id]
    assert full_rows[0].supersedes_id == original.id


def test_run_lock_blocks_second_active_run_until_release(db: ComicBookDB) -> None:
    db.acquire_run_lock(
        run_id="run-1",
        user_prompt="first run",
        started_at="2026-04-23T12:00:00Z",
        pid=101,
        host="host-a",
        router_prompt_version="ROUTER_SYSTEM_PROMPT_V2",
        pid_is_alive=lambda pid: True,
    )

    with pytest.raises(RunLockError):
        db.acquire_run_lock(
            run_id="run-2",
            user_prompt="second run",
            started_at="2026-04-23T12:01:00Z",
            pid=202,
            host="host-a",
            router_prompt_version="ROUTER_SYSTEM_PROMPT_V2",
            pid_is_alive=lambda pid: True,
        )

    db.release_run_lock("run-1")

    acquired = db.acquire_run_lock(
        run_id="run-2",
        user_prompt="second run",
        started_at="2026-04-23T12:01:00Z",
        pid=202,
        host="host-a",
        router_prompt_version="ROUTER_SYSTEM_PROMPT_V2",
        pid_is_alive=lambda pid: True,
    )

    assert acquired.run_id == "run-2"
    assert acquired.status == "running"


def test_stale_lock_is_recovered_only_for_dead_pid_on_same_host(db: ComicBookDB) -> None:
    db.acquire_run_lock(
        run_id="run-1",
        user_prompt="stale candidate",
        started_at="2026-04-23T12:00:00Z",
        pid=111,
        host="host-a",
        router_prompt_version="ROUTER_SYSTEM_PROMPT_V2",
        pid_is_alive=lambda pid: True,
    )

    acquired = db.acquire_run_lock(
        run_id="run-2",
        user_prompt="replacement run",
        started_at="2026-04-23T12:05:00Z",
        pid=222,
        host="host-a",
        router_prompt_version="ROUTER_SYSTEM_PROMPT_V2",
        pid_is_alive=lambda pid: False,
    )
    stale_run = db.get_run("run-1")

    assert acquired.run_id == "run-2"
    assert stale_run is not None
    assert stale_run.status == "failed"
    assert stale_run.pid is None
    assert stale_run.host is None


def test_prompt_and_image_round_trip(db: ComicBookDB) -> None:
    prompt = RenderedPrompt.model_validate(
        {
            "fingerprint": "fp-123",
            "subject_text": "Traveler portrait at sunrise.",
            "template_ids": ["storybook-soft"],
            "size": "1024x1536",
            "quality": "high",
            "image_model": "gpt-image-1.5",
            "rendered_prompt": "story style\n\n---\n\ntraveler portrait",
        }
    )

    inserted = db.upsert_prompt_if_absent(
        prompt=prompt,
        first_seen_run="run-1",
        created_at="2026-04-23T12:00:00Z",
    )
    duplicate = db.upsert_prompt_if_absent(
        prompt=prompt,
        first_seen_run="run-2",
        created_at="2026-04-23T12:10:00Z",
    )
    image = db.insert_image_result(
        fingerprint=prompt.fingerprint,
        run_id="run-1",
        created_at="2026-04-23T12:00:05Z",
        status="generated",
        file_path="image_output/run-1/001.png",
        bytes_written=128,
    )
    looked_up = db.get_prompt_by_fingerprint(prompt.fingerprint)
    existing_images = db.get_existing_images_by_fingerprint(prompt.fingerprint)

    assert duplicate.fingerprint == inserted.fingerprint
    assert duplicate.first_seen_run == "run-1"
    assert looked_up is not None
    assert looked_up.template_ids == ["storybook-soft"]
    assert image.status == "generated"
    assert [item.file_path for item in existing_images] == ["image_output/run-1/001.png"]


def test_daily_run_rollup_calculates_cache_hit_rate(db: ComicBookDB) -> None:
    first = db.acquire_run_lock(
        run_id="run-1",
        user_prompt="first",
        started_at="2026-04-23T08:00:00Z",
        pid=101,
        host="host-a",
        router_prompt_version="ROUTER_SYSTEM_PROMPT_V2",
        pid_is_alive=lambda pid: True,
    )
    db.finalize_run(
        run_id=first.run_id,
        ended_at="2026-04-23T08:05:00Z",
        status="succeeded",
        cache_hits=3,
        generated=1,
        failed=0,
        skipped_rate_limit=0,
        est_cost_usd=0.2,
    )
    second = db.acquire_run_lock(
        run_id="run-2",
        user_prompt="second",
        started_at="2026-04-23T09:00:00Z",
        pid=202,
        host="host-a",
        router_prompt_version="ROUTER_SYSTEM_PROMPT_V2",
        pid_is_alive=lambda pid: True,
    )
    db.finalize_run(
        run_id=second.run_id,
        ended_at="2026-04-23T09:05:00Z",
        status="partial",
        cache_hits=1,
        generated=3,
        failed=1,
        skipped_rate_limit=0,
        est_cost_usd=0.7,
    )

    rollup = db.get_daily_budget_rollup("2026-04-23")

    assert rollup is not None
    assert rollup.total_runs == 2
    assert rollup.total_cache_hits == 4
    assert rollup.total_generated == 4
    assert rollup.total_failed == 1
    assert rollup.total_est_cost_usd == pytest.approx(0.9)
    assert rollup.cache_hit_rate == pytest.approx(0.5)
