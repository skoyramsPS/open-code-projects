# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG1 foundation
- Last updated: 2026-04-23

## Scope of this slice

This slice implements the stable foundation contracts that later TaskGroups depend on:

- package and artifact directory layout under `ComicBook/`
- `pyproject.toml` with pinned workflow dependencies, including `langgraph~=`
- env-first configuration loading in `comicbook.config`
- typed workflow models and `RunState` in `comicbook.state`
- frozen dependency injection container in `comicbook.deps`

It intentionally does **not** add database, router, cache, graph, CLI, or image-client behavior yet.

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

## Local setup

1. Work from `ComicBook/`.
2. Copy values from `.env.example` into a local `.env` or export them in the shell.
3. Use `uv run --with pytest --with pydantic python -m pytest -q tests/test_config.py` for the current foundation test scope.

## Tests in this slice

`ComicBook/tests/test_config.py` currently verifies:

- `.env` loading and env precedence
- missing-config failure behavior
- parsing of known-good workflow models
- frozen `Deps` behavior

## Extension notes for the next slices

- TG2 should add `comicbook.db` without changing the config or state contracts unless a documented blocker appears.
- Nodes should consume `Deps` instead of reading global state or environment variables directly.
- New runtime behavior should continue to add narrow, direct unit tests before broader graph tests.
