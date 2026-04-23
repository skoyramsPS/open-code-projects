"""SQLite persistence and run-lock DAO for the comicbook workflow."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from comicbook.state import RenderedPrompt, TemplateSummary


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS templates (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    style_text       TEXT NOT NULL,
    style_text_hash  TEXT NOT NULL,
    tags             TEXT NOT NULL,
    summary          TEXT NOT NULL,
    supersedes_id    TEXT NULL REFERENCES templates(id),
    created_at       TEXT NOT NULL,
    created_by_run   TEXT,
    UNIQUE(name, style_text_hash)
);

CREATE TABLE IF NOT EXISTS prompts (
    fingerprint      TEXT PRIMARY KEY,
    rendered_prompt  TEXT NOT NULL,
    subject_text     TEXT NOT NULL,
    template_ids     TEXT NOT NULL,
    size             TEXT NOT NULL,
    quality          TEXT NOT NULL,
    image_model      TEXT NOT NULL,
    first_seen_run   TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS images (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint      TEXT NOT NULL REFERENCES prompts(fingerprint),
    file_path        TEXT,
    bytes            INTEGER NOT NULL DEFAULT 0,
    run_id           TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    status           TEXT NOT NULL,
    failure_reason   TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    run_id                TEXT PRIMARY KEY,
    user_prompt           TEXT NOT NULL,
    router_model          TEXT,
    router_prompt_version TEXT,
    plan_json             TEXT,
    started_at            TEXT NOT NULL,
    ended_at              TEXT,
    status                TEXT NOT NULL,
    pid                   INTEGER,
    host                  TEXT,
    cache_hits            INTEGER DEFAULT 0,
    generated             INTEGER DEFAULT 0,
    failed                INTEGER DEFAULT 0,
    skipped_rate_limit    INTEGER DEFAULT 0,
    est_cost_usd          REAL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS ix_images_run ON images(run_id);
CREATE INDEX IF NOT EXISTS ix_prompts_first_seen ON prompts(first_seen_run);
CREATE INDEX IF NOT EXISTS ix_runs_status ON runs(status);

CREATE VIEW IF NOT EXISTS daily_run_rollup AS
SELECT
    substr(started_at, 1, 10) AS run_date,
    COUNT(*) AS total_runs,
    COALESCE(SUM(cache_hits), 0) AS total_cache_hits,
    COALESCE(SUM(generated), 0) AS total_generated,
    COALESCE(SUM(failed), 0) AS total_failed,
    COALESCE(SUM(est_cost_usd), 0.0) AS total_est_cost_usd,
    CASE
        WHEN COALESCE(SUM(cache_hits), 0) + COALESCE(SUM(generated), 0) = 0 THEN 0.0
        ELSE CAST(COALESCE(SUM(cache_hits), 0) AS REAL)
             / CAST(COALESCE(SUM(cache_hits), 0) + COALESCE(SUM(generated), 0) AS REAL)
    END AS cache_hit_rate
FROM runs
GROUP BY substr(started_at, 1, 10);
"""


class RunLockError(RuntimeError):
    """Raised when another active run already holds the database lock."""


PidIsAlive = Callable[[int], bool]


@dataclass(frozen=True, slots=True)
class TemplateRecord:
    id: str
    name: str
    style_text: str
    style_text_hash: str
    tags: list[str]
    summary: str
    supersedes_id: str | None
    created_at: str
    created_by_run: str | None


@dataclass(frozen=True, slots=True)
class PromptRecord:
    fingerprint: str
    rendered_prompt: str
    subject_text: str
    template_ids: list[str]
    size: str
    quality: str
    image_model: str
    first_seen_run: str
    created_at: str


@dataclass(frozen=True, slots=True)
class ImageRecord:
    id: int
    fingerprint: str
    file_path: str | None
    bytes: int
    run_id: str
    created_at: str
    status: str
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    user_prompt: str
    router_model: str | None
    router_prompt_version: str | None
    plan_json: str | None
    started_at: str
    ended_at: str | None
    status: str
    pid: int | None
    host: str | None
    cache_hits: int
    generated: int
    failed: int
    skipped_rate_limit: int
    est_cost_usd: float


@dataclass(frozen=True, slots=True)
class DailyRunRollup:
    run_date: str
    total_runs: int
    total_cache_hits: int
    total_generated: int
    total_failed: int
    total_est_cost_usd: float
    cache_hit_rate: float


class ComicBookDB:
    """Repository-scoped SQLite DAO with explicit workflow helpers."""

    def __init__(self, connection: sqlite3.Connection, db_path: str | Path) -> None:
        self.connection = connection
        self.db_path = Path(db_path)

    @classmethod
    def connect(cls, db_path: str | Path) -> "ComicBookDB":
        connection = sqlite3.connect(Path(db_path), timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        database = cls(connection=connection, db_path=db_path)
        database.initialize()
        return database

    def close(self) -> None:
        self.connection.close()

    def initialize(self) -> None:
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.enable_wal()
        self.init_schema()

    def enable_wal(self) -> str:
        result = self.connection.execute("PRAGMA journal_mode = WAL").fetchone()
        self.connection.commit()
        return str(result[0]) if result else "wal"

    def init_schema(self) -> None:
        self.connection.executescript(SCHEMA_SQL)
        self.connection.commit()

    def is_stale_lock(self, pid: int | None, host: str | None, current_host: str, pid_is_alive: PidIsAlive) -> bool:
        if pid is None or host is None or host != current_host:
            return False
        return not pid_is_alive(pid)

    def create_run(
        self,
        *,
        run_id: str,
        user_prompt: str,
        started_at: str,
        status: str,
        pid: int | None = None,
        host: str | None = None,
        router_prompt_version: str | None = None,
    ) -> RunRecord:
        self.connection.execute(
            """
            INSERT INTO runs (
                run_id, user_prompt, router_prompt_version, started_at, status, pid, host
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                user_prompt=excluded.user_prompt,
                router_prompt_version=excluded.router_prompt_version,
                started_at=excluded.started_at,
                status=excluded.status,
                pid=excluded.pid,
                host=excluded.host
            """,
            (run_id, user_prompt, router_prompt_version, started_at, status, pid, host),
        )
        self.connection.commit()
        record = self.get_run(run_id)
        if record is None:  # pragma: no cover - defensive after an INSERT/UPDATE
            raise RuntimeError(f"Failed to create run record for {run_id}")
        return record

    def acquire_run_lock(
        self,
        *,
        run_id: str,
        user_prompt: str,
        started_at: str,
        pid: int,
        host: str,
        router_prompt_version: str | None,
        pid_is_alive: PidIsAlive,
    ) -> RunRecord:
        active = self.connection.execute(
            """
            SELECT *
            FROM runs
            WHERE status = ? AND pid IS NOT NULL AND host IS NOT NULL AND run_id != ?
            ORDER BY started_at
            LIMIT 1
            """,
            ("running", run_id),
        ).fetchone()

        if active is not None:
            if self.is_stale_lock(active["pid"], active["host"], host, pid_is_alive):
                self.connection.execute(
                    """
                    UPDATE runs
                    SET status = ?, ended_at = ?, pid = NULL, host = NULL
                    WHERE run_id = ?
                    """,
                    ("failed", started_at, active["run_id"]),
                )
                self.connection.commit()
            else:
                raise RunLockError(
                    f"Database lock is held by run {active['run_id']} on host {active['host']} pid {active['pid']}"
                )

        return self.create_run(
            run_id=run_id,
            user_prompt=user_prompt,
            started_at=started_at,
            status="running",
            pid=pid,
            host=host,
            router_prompt_version=router_prompt_version,
        )

    def release_run_lock(self, run_id: str) -> None:
        self.connection.execute(
            "UPDATE runs SET pid = NULL, host = NULL WHERE run_id = ?",
            (run_id,),
        )
        self.connection.commit()

    def finalize_run(
        self,
        *,
        run_id: str,
        ended_at: str,
        status: str,
        cache_hits: int,
        generated: int,
        failed: int,
        skipped_rate_limit: int,
        est_cost_usd: float,
        router_model: str | None = None,
        router_prompt_version: str | None = None,
        plan_json: str | dict[str, object] | None = None,
    ) -> RunRecord:
        serialized_plan = json.dumps(plan_json, sort_keys=True) if isinstance(plan_json, dict) else plan_json
        self.connection.execute(
            """
            UPDATE runs
            SET ended_at = ?,
                status = ?,
                cache_hits = ?,
                generated = ?,
                failed = ?,
                skipped_rate_limit = ?,
                est_cost_usd = ?,
                router_model = COALESCE(?, router_model),
                router_prompt_version = COALESCE(?, router_prompt_version),
                plan_json = COALESCE(?, plan_json),
                pid = NULL,
                host = NULL
            WHERE run_id = ?
            """,
            (
                ended_at,
                status,
                cache_hits,
                generated,
                failed,
                skipped_rate_limit,
                est_cost_usd,
                router_model,
                router_prompt_version,
                serialized_plan,
                run_id,
            ),
        )
        self.connection.commit()
        record = self.get_run(run_id)
        if record is None:  # pragma: no cover - defensive after UPDATE
            raise RuntimeError(f"Failed to finalize run record for {run_id}")
        return record

    def get_run(self, run_id: str) -> RunRecord | None:
        row = self.connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row_to_run_record(row) if row is not None else None

    def list_template_summaries(self) -> list[TemplateSummary]:
        rows = self.connection.execute(
            "SELECT id, name, tags, summary, created_at FROM templates ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [
            TemplateSummary.model_validate(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "tags": json.loads(row["tags"]),
                    "summary": row["summary"],
                    "created_at": row["created_at"],
                }
            )
            for row in rows
        ]

    def get_templates_by_ids(self, template_ids: Sequence[str]) -> list[TemplateRecord]:
        if not template_ids:
            return []
        placeholders = ", ".join("?" for _ in template_ids)
        rows = self.connection.execute(
            f"SELECT * FROM templates WHERE id IN ({placeholders})",
            tuple(template_ids),
        ).fetchall()
        records_by_id = {row["id"]: self._row_to_template_record(row) for row in rows}
        return [records_by_id[template_id] for template_id in template_ids if template_id in records_by_id]

    def insert_template(
        self,
        *,
        template_id: str,
        name: str,
        style_text: str,
        tags: Iterable[str],
        summary: str,
        created_at: str,
        created_by_run: str | None,
        supersedes_id: str | None = None,
    ) -> TemplateRecord:
        style_text_hash = hashlib.sha256(style_text.encode("utf-8")).hexdigest()
        tags_json = json.dumps(list(tags), sort_keys=True)
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO templates (
                id, name, style_text, style_text_hash, tags, summary, supersedes_id, created_at, created_by_run
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                name,
                style_text,
                style_text_hash,
                tags_json,
                summary,
                supersedes_id,
                created_at,
                created_by_run,
            ),
        )
        self.connection.commit()

        if cursor.rowcount == 0:
            row = self.connection.execute(
                "SELECT * FROM templates WHERE name = ? AND style_text_hash = ?",
                (name, style_text_hash),
            ).fetchone()
        else:
            row = self.connection.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()

        if row is None:  # pragma: no cover - defensive after insert
            raise RuntimeError(f"Failed to fetch template record for {template_id}")
        return self._row_to_template_record(row)

    def upsert_prompt_if_absent(self, *, prompt: RenderedPrompt, first_seen_run: str, created_at: str) -> PromptRecord:
        fingerprint = prompt.fingerprint
        if fingerprint is None:
            raise ValueError("RenderedPrompt.fingerprint is required before prompt persistence")

        self.connection.execute(
            """
            INSERT OR IGNORE INTO prompts (
                fingerprint, rendered_prompt, subject_text, template_ids, size, quality, image_model, first_seen_run, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fingerprint,
                prompt.rendered_prompt,
                prompt.subject_text,
                json.dumps(prompt.template_ids),
                prompt.size,
                prompt.quality,
                prompt.image_model,
                first_seen_run,
                created_at,
            ),
        )
        self.connection.commit()
        record = self.get_prompt_by_fingerprint(fingerprint)
        if record is None:  # pragma: no cover - defensive after insert
            raise RuntimeError(f"Failed to fetch prompt record for {fingerprint}")
        return record

    def get_prompt_by_fingerprint(self, fingerprint: str) -> PromptRecord | None:
        row = self.connection.execute(
            "SELECT * FROM prompts WHERE fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        return self._row_to_prompt_record(row) if row is not None else None

    def insert_image_result(
        self,
        *,
        fingerprint: str,
        run_id: str,
        created_at: str,
        status: str,
        file_path: str | None = None,
        bytes_written: int = 0,
        failure_reason: str | None = None,
    ) -> ImageRecord:
        cursor = self.connection.execute(
            """
            INSERT INTO images (fingerprint, file_path, bytes, run_id, created_at, status, failure_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fingerprint, file_path, bytes_written, run_id, created_at, status, failure_reason),
        )
        self.connection.commit()
        row = self.connection.execute("SELECT * FROM images WHERE id = ?", (cursor.lastrowid,)).fetchone()
        if row is None:  # pragma: no cover - defensive after insert
            raise RuntimeError(f"Failed to fetch inserted image row for {fingerprint}")
        return self._row_to_image_record(row)

    def get_existing_images_by_fingerprint(self, fingerprint: str) -> list[ImageRecord]:
        rows = self.connection.execute(
            "SELECT * FROM images WHERE fingerprint = ? ORDER BY created_at, id",
            (fingerprint,),
        ).fetchall()
        return [self._row_to_image_record(row) for row in rows]

    def get_daily_budget_rollup(self, run_date: str) -> DailyRunRollup | None:
        row = self.connection.execute(
            "SELECT * FROM daily_run_rollup WHERE run_date = ?",
            (run_date,),
        ).fetchone()
        if row is None:
            return None
        return DailyRunRollup(
            run_date=row["run_date"],
            total_runs=row["total_runs"],
            total_cache_hits=row["total_cache_hits"],
            total_generated=row["total_generated"],
            total_failed=row["total_failed"],
            total_est_cost_usd=row["total_est_cost_usd"],
            cache_hit_rate=row["cache_hit_rate"],
        )

    @staticmethod
    def _row_to_template_record(row: sqlite3.Row) -> TemplateRecord:
        return TemplateRecord(
            id=row["id"],
            name=row["name"],
            style_text=row["style_text"],
            style_text_hash=row["style_text_hash"],
            tags=json.loads(row["tags"]),
            summary=row["summary"],
            supersedes_id=row["supersedes_id"],
            created_at=row["created_at"],
            created_by_run=row["created_by_run"],
        )

    @staticmethod
    def _row_to_prompt_record(row: sqlite3.Row) -> PromptRecord:
        return PromptRecord(
            fingerprint=row["fingerprint"],
            rendered_prompt=row["rendered_prompt"],
            subject_text=row["subject_text"],
            template_ids=json.loads(row["template_ids"]),
            size=row["size"],
            quality=row["quality"],
            image_model=row["image_model"],
            first_seen_run=row["first_seen_run"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_image_record(row: sqlite3.Row) -> ImageRecord:
        return ImageRecord(
            id=row["id"],
            fingerprint=row["fingerprint"],
            file_path=row["file_path"],
            bytes=row["bytes"],
            run_id=row["run_id"],
            created_at=row["created_at"],
            status=row["status"],
            failure_reason=row["failure_reason"],
        )

    @staticmethod
    def _row_to_run_record(row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            user_prompt=row["user_prompt"],
            router_model=row["router_model"],
            router_prompt_version=row["router_prompt_version"],
            plan_json=row["plan_json"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"],
            pid=row["pid"],
            host=row["host"],
            cache_hits=row["cache_hits"],
            generated=row["generated"],
            failed=row["failed"],
            skipped_rate_limit=row["skipped_rate_limit"],
            est_cost_usd=row["est_cost_usd"],
        )


__all__ = [
    "ComicBookDB",
    "DailyRunRollup",
    "ImageRecord",
    "PromptRecord",
    "RunLockError",
    "RunRecord",
    "TemplateRecord",
]
