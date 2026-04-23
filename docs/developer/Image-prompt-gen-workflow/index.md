# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG2 persistence and locking
- Last updated: 2026-04-23

## Scope of this slice

This slice implements the stable foundation contracts that later TaskGroups depend on:

- package and artifact directory layout under `ComicBook/`
- `pyproject.toml` with pinned workflow dependencies, including `langgraph~=`
- env-first configuration loading in `comicbook.config`
- typed workflow models and `RunState` in `comicbook.state`
- frozen dependency injection container in `comicbook.deps`
- `comicbook.db` SQLite DAO with idempotent schema creation, WAL startup, run locking, and persistence helpers for templates, prompts, images, and run summaries

It intentionally still does **not** add router, graph, CLI, or image-client behavior yet.

## Module responsibilities

### `comicbook.config`

- loads environment variables with `.env` fallback
- validates required Azure settings
- normalizes defaults for DB path, output directories, router models, and router prompt version
- keeps `.env` parsing local to this package so the read-only reference scripts remain untouched

### `comicbook.state`

Defines the durable schema boundary for later nodes and tests:

- `TemplateSummary`
- `NewTemplateDraft`
- `PromptPlanItem`
- `RouterTemplateDecision`
- `RouterPlan`
- `RenderedPrompt`
- `ImageResult`
- `WorkflowError`
- `UsageTotals`
- `RunSummary`
- `RunState` typed graph contract

Notable validations already in place:

- `NewTemplateDraft.id` must be a lowercase slug
- `RouterPlan.rationale` is capped at 600 characters
- `RouterPlan` requires an escalation reason when escalation is requested
- router prompt items reject empty `subject_text`

### `comicbook.deps`

`Deps` is a frozen dataclass that carries runtime collaborators explicitly:

- `config`
- `db`
- `http_client`
- `clock`
- `uuid_factory`
- `output_dir`
- `runs_dir`
- `logs_dir`
- `pricing`
- `logger`
- `pid_provider`
- `hostname_provider`

Optional test-facing fields are reserved for fake router transport, fake image transport, and filesystem abstractions.

### `comicbook.db`

`ComicBookDB` is now the repository's SQLite boundary for workflow persistence.

Implemented responsibilities:

- open one shared SQLite connection per process
- enable `PRAGMA journal_mode=WAL`
- create the required tables, indexes, and `daily_run_rollup` view idempotently
- acquire and release the one-run-at-a-time lock using the `runs` table
- recover stale locks only when the recorded PID is dead on the same host
- insert templates with append-only lineage and duplicate suppression on `(name, style_text_hash)`
- persist prompt rows before later image generation work
- persist image result rows and look them up by prompt fingerprint
- finalize run summary counters and estimated cost totals

Current record types exported from `comicbook.db`:

- `TemplateRecord`
- `PromptRecord`
- `ImageRecord`
- `RunRecord`
- `DailyRunRollup`
- `RunLockError`

Operational note:

- active-lock detection only treats `runs` rows with `status='running'` and non-null `pid`/`host` as lock holders, so lock release clears ownership without rewriting historical counters.

## Local setup

1. Work from `ComicBook/`.
2. Copy values from `.env.example` into a local `.env` or export them in the shell.
3. Use `uv run --with pytest --with pydantic python -m pytest -q tests/test_config.py tests/test_db.py` for the current focused test scope.

## Tests in this slice

`ComicBook/tests/test_config.py` currently verifies:

- `.env` loading and env precedence
- missing-config failure behavior
- parsing of known-good workflow models
- frozen `Deps` behavior

`ComicBook/tests/test_db.py` now verifies:

- schema initialization idempotency and WAL mode
- template deduplication and append-only lineage support
- active run lock blocking and explicit lock release behavior
- stale-lock recovery for dead same-host PIDs
- prompt/image persistence round trips
- daily run rollup and cache-hit-rate calculation

## Extension notes for the next slices

- TG3 should build router and template-loading logic on DAO methods only, without embedding raw SQL in nodes.
- Nodes should consume `Deps` instead of reading global state or environment variables directly.
- New runtime behavior should continue to add narrow, direct unit tests before broader graph tests.
