"""SQLite persistence and run-lock DAO shared across workflows."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, Sequence, TypeVar


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

CREATE TABLE IF NOT EXISTS import_runs (
    import_run_id        TEXT PRIMARY KEY,
    source_file_path     TEXT,
    source_file_hash     TEXT NOT NULL,
    started_at           TEXT NOT NULL,
    ended_at             TEXT,
    status               TEXT NOT NULL,
    pid                  INTEGER,
    host                 TEXT,
    dry_run              INTEGER NOT NULL DEFAULT 0,
    total_rows           INTEGER NOT NULL DEFAULT 0,
    inserted             INTEGER NOT NULL DEFAULT 0,
    updated              INTEGER NOT NULL DEFAULT 0,
    skipped_duplicate    INTEGER NOT NULL DEFAULT 0,
    skipped_resume       INTEGER NOT NULL DEFAULT 0,
    failed               INTEGER NOT NULL DEFAULT 0,
    backfilled           INTEGER NOT NULL DEFAULT 0,
    warnings             INTEGER NOT NULL DEFAULT 0,
    est_cost_usd         REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS import_row_results (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id           TEXT NOT NULL REFERENCES import_runs(import_run_id),
    source_file_hash        TEXT NOT NULL,
    row_index               INTEGER NOT NULL,
    template_id             TEXT,
    status                  TEXT NOT NULL,
    reason                  TEXT,
    warnings_json           TEXT,
    requested_supersedes_id TEXT,
    persisted_supersedes_id TEXT,
    diff_json               TEXT,
    backfill_raw            TEXT,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL,
    UNIQUE(import_run_id, row_index)
);

CREATE INDEX IF NOT EXISTS ix_images_run ON images(run_id);
CREATE INDEX IF NOT EXISTS ix_import_runs_status ON import_runs(status);
CREATE INDEX IF NOT EXISTS ix_import_row_results_hash_row ON import_row_results(source_file_hash, row_index);
CREATE INDEX IF NOT EXISTS ix_import_row_results_template ON import_row_results(template_id);
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


class PromptLike(Protocol):
    fingerprint: str | None
    rendered_prompt: str
    subject_text: str
    template_ids: Sequence[str]
    size: str
    quality: str
    image_model: str


TSummary = TypeVar("TSummary")


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
class ImportRunRecord:
    import_run_id: str
    source_file_path: str | None
    source_file_hash: str
    started_at: str
    ended_at: str | None
    status: str
    pid: int | None
    host: str | None
    dry_run: bool
    total_rows: int
    inserted: int
    updated: int
    skipped_duplicate: int
    skipped_resume: int
    failed: int
    backfilled: int
    warnings: int
    est_cost_usd: float


@dataclass(frozen=True, slots=True)
class ImportRowResultRecord:
    id: int
    import_run_id: str
    source_file_hash: str
    row_index: int
    template_id: str | None
    status: str
    reason: str | None
    warnings: list[str]
    requested_supersedes_id: str | None
    persisted_supersedes_id: str | None
    diff: dict[str, Any] | None
    backfill_raw: str | None
    retry_count: int
    created_at: str


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

    @staticmethod
    def _style_text_hash(style_text: str) -> str:
        return hashlib.sha256(style_text.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize_json(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, sort_keys=True)

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

    def create_import_run(
        self,
        *,
        import_run_id: str,
        source_file_path: str | None,
        source_file_hash: str,
        started_at: str,
        status: str,
        dry_run: bool,
        pid: int | None = None,
        host: str | None = None,
    ) -> ImportRunRecord:
        self.connection.execute(
            """
            INSERT INTO import_runs (
                import_run_id, source_file_path, source_file_hash, started_at, status, dry_run, pid, host
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(import_run_id) DO UPDATE SET
                source_file_path=excluded.source_file_path,
                source_file_hash=excluded.source_file_hash,
                started_at=excluded.started_at,
                status=excluded.status,
                dry_run=excluded.dry_run,
                pid=excluded.pid,
                host=excluded.host
            """,
            (import_run_id, source_file_path, source_file_hash, started_at, status, int(dry_run), pid, host),
        )
        self.connection.commit()
        record = self.get_import_run(import_run_id)
        if record is None:  # pragma: no cover - defensive after an INSERT/UPDATE
            raise RuntimeError(f"Failed to create import run record for {import_run_id}")
        return record

    def acquire_import_lock(
        self,
        *,
        import_run_id: str,
        source_file_path: str | None,
        source_file_hash: str,
        started_at: str,
        dry_run: bool,
        pid: int,
        host: str,
        pid_is_alive: PidIsAlive,
    ) -> ImportRunRecord:
        active = self.connection.execute(
            """
            SELECT *
            FROM import_runs
            WHERE status = ? AND pid IS NOT NULL AND host IS NOT NULL AND import_run_id != ?
            ORDER BY started_at
            LIMIT 1
            """,
            ("running", import_run_id),
        ).fetchone()

        if active is not None:
            if self.is_stale_lock(active["pid"], active["host"], host, pid_is_alive):
                self.connection.execute(
                    """
                    UPDATE import_runs
                    SET status = ?, ended_at = ?, pid = NULL, host = NULL
                    WHERE import_run_id = ?
                    """,
                    ("failed", started_at, active["import_run_id"]),
                )
                self.connection.commit()
            else:
                raise RunLockError(
                    "Database import lock is held by run "
                    f"{active['import_run_id']} on host {active['host']} pid {active['pid']}"
                )

        return self.create_import_run(
            import_run_id=import_run_id,
            source_file_path=source_file_path,
            source_file_hash=source_file_hash,
            started_at=started_at,
            status="running",
            dry_run=dry_run,
            pid=pid,
            host=host,
        )

    def release_import_lock(self, import_run_id: str) -> None:
        self.connection.execute(
            "UPDATE import_runs SET pid = NULL, host = NULL WHERE import_run_id = ?",
            (import_run_id,),
        )
        self.connection.commit()

    def finalize_import_run(
        self,
        *,
        import_run_id: str,
        ended_at: str,
        status: str,
        total_rows: int = 0,
        inserted: int = 0,
        updated: int = 0,
        skipped_duplicate: int = 0,
        skipped_resume: int = 0,
        failed: int = 0,
        backfilled: int = 0,
        warnings: int = 0,
        est_cost_usd: float = 0.0,
    ) -> ImportRunRecord:
        self.connection.execute(
            """
            UPDATE import_runs
            SET ended_at = ?,
                status = ?,
                total_rows = ?,
                inserted = ?,
                updated = ?,
                skipped_duplicate = ?,
                skipped_resume = ?,
                failed = ?,
                backfilled = ?,
                warnings = ?,
                est_cost_usd = ?,
                pid = NULL,
                host = NULL
            WHERE import_run_id = ?
            """,
            (
                ended_at,
                status,
                total_rows,
                inserted,
                updated,
                skipped_duplicate,
                skipped_resume,
                failed,
                backfilled,
                warnings,
                est_cost_usd,
                import_run_id,
            ),
        )
        self.connection.commit()
        record = self.get_import_run(import_run_id)
        if record is None:  # pragma: no cover - defensive after UPDATE
            raise RuntimeError(f"Failed to finalize import run record for {import_run_id}")
        return record

    def get_import_run(self, import_run_id: str) -> ImportRunRecord | None:
        row = self.connection.execute(
            "SELECT * FROM import_runs WHERE import_run_id = ?",
            (import_run_id,),
        ).fetchone()
        return self._row_to_import_run_record(row) if row is not None else None

    def get_terminal_row_results_by_hash(self, source_file_hash: str) -> list[ImportRowResultRecord]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM import_row_results
            WHERE source_file_hash = ?
            ORDER BY row_index ASC, created_at DESC, id DESC
            """,
            (source_file_hash,),
        ).fetchall()
        latest_by_row_index: dict[int, ImportRowResultRecord] = {}
        for row in rows:
            row_index = int(row["row_index"])
            if row_index not in latest_by_row_index:
                latest_by_row_index[row_index] = self._row_to_import_row_result_record(row)
        return [latest_by_row_index[row_index] for row_index in sorted(latest_by_row_index)]

    def record_import_row_result(
        self,
        *,
        import_run_id: str,
        source_file_hash: str,
        row_index: int,
        template_id: str | None,
        status: str,
        created_at: str,
        reason: str | None = None,
        warnings: list[str] | None = None,
        requested_supersedes_id: str | None = None,
        persisted_supersedes_id: str | None = None,
        diff: dict[str, Any] | None = None,
        backfill_raw: str | None = None,
        retry_count: int = 0,
    ) -> ImportRowResultRecord:
        self.connection.execute(
            """
            INSERT INTO import_row_results (
                import_run_id,
                source_file_hash,
                row_index,
                template_id,
                status,
                reason,
                warnings_json,
                requested_supersedes_id,
                persisted_supersedes_id,
                diff_json,
                backfill_raw,
                retry_count,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(import_run_id, row_index) DO UPDATE SET
                template_id=excluded.template_id,
                status=excluded.status,
                reason=excluded.reason,
                warnings_json=excluded.warnings_json,
                requested_supersedes_id=excluded.requested_supersedes_id,
                persisted_supersedes_id=excluded.persisted_supersedes_id,
                diff_json=excluded.diff_json,
                backfill_raw=excluded.backfill_raw,
                retry_count=excluded.retry_count,
                created_at=excluded.created_at
            """,
            (
                import_run_id,
                source_file_hash,
                row_index,
                template_id,
                status,
                reason,
                self._serialize_json(warnings or []),
                requested_supersedes_id,
                persisted_supersedes_id,
                self._serialize_json(diff),
                backfill_raw,
                retry_count,
                created_at,
            ),
        )
        self.connection.commit()
        row = self.connection.execute(
            "SELECT * FROM import_row_results WHERE import_run_id = ? AND row_index = ?",
            (import_run_id, row_index),
        ).fetchone()
        if row is None:  # pragma: no cover - defensive after insert/update
            raise RuntimeError(f"Failed to fetch import row result for {import_run_id}:{row_index}")
        return self._row_to_import_row_result_record(row)

    def list_template_summaries(self, *, summary_factory: Callable[[dict[str, object]], TSummary]) -> list[TSummary]:
        rows = self.connection.execute(
            "SELECT id, name, tags, summary, created_at FROM templates ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [
            summary_factory(
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

    def get_template_by_id(self, template_id: str) -> TemplateRecord | None:
        row = self.connection.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
        return self._row_to_template_record(row) if row is not None else None

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
        style_text_hash = self._style_text_hash(style_text)
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

    def update_template_in_place(
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
        style_text_hash = self._style_text_hash(style_text)
        tags_json = json.dumps(list(tags), sort_keys=True)
        self.connection.execute(
            """
            UPDATE templates
            SET name = ?,
                style_text = ?,
                style_text_hash = ?,
                tags = ?,
                summary = ?,
                supersedes_id = ?,
                created_at = ?,
                created_by_run = ?
            WHERE id = ?
            """,
            (
                name,
                style_text,
                style_text_hash,
                tags_json,
                summary,
                supersedes_id,
                created_at,
                created_by_run,
                template_id,
            ),
        )
        self.connection.commit()
        row = self.connection.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
        if row is None:
            raise RuntimeError(f"Failed to fetch updated template record for {template_id}")
        return self._row_to_template_record(row)

    def count_prompt_rows_for_template_hash(self, style_text_hash: str) -> int:
        template_ids = [
            row["id"]
            for row in self.connection.execute(
                "SELECT id FROM templates WHERE style_text_hash = ?",
                (style_text_hash,),
            ).fetchall()
        ]
        if not template_ids:
            return 0

        count = 0
        for row in self.connection.execute("SELECT template_ids FROM prompts").fetchall():
            prompt_template_ids = json.loads(row["template_ids"])
            if any(template_id in prompt_template_ids for template_id in template_ids):
                count += 1
        return count

    def upsert_prompt_if_absent(self, *, prompt: PromptLike, first_seen_run: str, created_at: str) -> PromptRecord:
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
    def _row_to_import_run_record(row: sqlite3.Row) -> ImportRunRecord:
        return ImportRunRecord(
            import_run_id=row["import_run_id"],
            source_file_path=row["source_file_path"],
            source_file_hash=row["source_file_hash"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"],
            pid=row["pid"],
            host=row["host"],
            dry_run=bool(row["dry_run"]),
            total_rows=row["total_rows"],
            inserted=row["inserted"],
            updated=row["updated"],
            skipped_duplicate=row["skipped_duplicate"],
            skipped_resume=row["skipped_resume"],
            failed=row["failed"],
            backfilled=row["backfilled"],
            warnings=row["warnings"],
            est_cost_usd=row["est_cost_usd"],
        )

    @staticmethod
    def _row_to_import_row_result_record(row: sqlite3.Row) -> ImportRowResultRecord:
        warnings_json = row["warnings_json"]
        diff_json = row["diff_json"]
        return ImportRowResultRecord(
            id=row["id"],
            import_run_id=row["import_run_id"],
            source_file_hash=row["source_file_hash"],
            row_index=row["row_index"],
            template_id=row["template_id"],
            status=row["status"],
            reason=row["reason"],
            warnings=json.loads(warnings_json) if warnings_json else [],
            requested_supersedes_id=row["requested_supersedes_id"],
            persisted_supersedes_id=row["persisted_supersedes_id"],
            diff=json.loads(diff_json) if diff_json else None,
            backfill_raw=row["backfill_raw"],
            retry_count=row["retry_count"],
            created_at=row["created_at"],
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
    "ImportRowResultRecord",
    "ImportRunRecord",
    "ImageRecord",
    "PidIsAlive",
    "PromptRecord",
    "RunLockError",
    "RunRecord",
    "SCHEMA_SQL",
    "TemplateRecord",
]
