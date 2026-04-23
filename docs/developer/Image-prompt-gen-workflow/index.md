# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG3 router-planning complete, including the live router transport cluster
- Last updated: 2026-04-23

## Scope of this slice

This slice implements the stable foundation contracts that later TaskGroups depend on:

- package and artifact directory layout under `ComicBook/`
- `pyproject.toml` with pinned workflow dependencies, including `langgraph~=`
- env-first configuration loading in `comicbook.config`
- typed workflow models and `RunState` in `comicbook.state`
- frozen dependency injection container in `comicbook.deps`
- `comicbook.db` SQLite DAO with idempotent schema creation, WAL startup, run locking, and persistence helpers for templates, prompts, images, and run summaries
- `comicbook.router_prompts` for the versioned router system prompt, authoritative JSON schema export, workflow-specific router validation, rationale leak redaction, and deterministic template pre-filtering
- `comicbook.nodes.load_templates` for loading the full template catalog plus the router-visible subset into state
- `comicbook.router_llm` for the reusable Responses API call path, repair prompt construction, usage extraction, and validated router-plan requests
- `comicbook.nodes.router` for the workflow node that executes the fallback call, optional repair, optional escalation, and usage accumulation

It intentionally still does **not** add prompt materialization, template persistence, cache lookup, graph wiring, CLI execution, or image-client behavior yet.

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

### `comicbook.router_prompts`

This module now owns the reusable router planning contract that later router transport code calls:

- `ROUTER_SYSTEM_PROMPT_V2` as the stable system prompt string persisted by config/version references
- `ROUTER_PLAN_JSON_SCHEMA` and `ROUTER_RESPONSE_FORMAT` for strict structured-output calls
- `validate_router_plan(...)` for parsing a raw router payload into `RouterPlan` and enforcing workflow rules beyond bare schema checks
- `sanitize_rationale_text(...)` for the v1 rationale leak guard
- `select_templates_for_router(...)` for the deterministic large-catalog lexical pre-filter

Workflow-specific validation enforced here today:

- exact image count can be required via `exact_image_count`
- `template_decision.selected_template_ids` must all exist in the router-visible template subset
- prompt item `template_ids` must come from that selected subset or from the same response's `new_template.id`
- rationale text is truncated to 600 chars and redacted if it appears to leak the leading system-prompt fragment

### `comicbook.router_llm`

This module now owns the reusable live router client for JSON-schema-constrained Responses API calls.

Implemented responsibilities:

- build the router-visible JSON payload with `user_prompt`, `known_templates`, workflow constraints, and the available router models
- send a stable two-message system/user request to `{endpoint}/openai/responses?api-version=...`
- include `response_format={type: json_schema, ...}` and `temperature=0` on every router request
- extract output text and token usage from the provider response payload
- perform exactly one repair retry when the first response fails schema or workflow validation
- reject responses whose `router_model_chosen` echo does not match the model that was actually requested

Current public helpers:

- `build_router_input_payload(...)`
- `build_router_request_messages(...)`
- `call_router_response(...)`
- `request_router_plan(...)`

### `comicbook.nodes.load_templates`

The node contract is intentionally narrow:

- requires `state["user_prompt"]`
- reads template summaries through `deps.db.list_template_summaries()` only
- returns `templates`, `template_catalog_size`, and `templates_sent_to_router`
- keeps the full catalog in state even when the router-visible subset is filtered to 15 entries

### `comicbook.nodes.router`

The router node now performs the full TG3 router-planning workflow stage:

- requires `state["user_prompt"]`
- reads `state["templates_sent_to_router"]` as the authoritative router-visible template subset
- starts on `config.comicbook_router_model_fallback`
- performs one repair retry if validation fails
- escalates once to `config.comicbook_router_model_escalation` when the validated fallback plan sets `needs_escalation=true`
- returns `router_model`, `plan`, `plan_raw`, `plan_repair_attempts`, `router_escalated`, and updated `usage`

Implementation note:

- the router node intentionally does not compose final rendered prompts or persist new templates; those remain in TG4.

## Local setup

1. Work from `ComicBook/`.
2. Copy values from `.env.example` into a local `.env` or export them in the shell.
3. Use `uv run --with pytest --with pydantic python -m pytest -q tests/test_config.py tests/test_db.py tests/test_router_validation.py tests/test_node_load_templates.py tests/test_router_node.py` for the current focused unit-test scope.

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

`ComicBook/tests/test_router_validation.py` now verifies:

- valid router payload parsing into `RouterPlan`
- rationale leak redaction
- rejection of unknown prompt template IDs
- exact-image-count validation
- deterministic template pre-filter ranking and all-zero fallback behavior

`ComicBook/tests/test_node_load_templates.py` now verifies:

- full-catalog behavior when the template count is 30 or fewer
- deterministic top-15 router subset behavior when the catalog is larger than 30

`ComicBook/tests/test_router_node.py` now verifies:

- the router node sends the expected Responses API URL, model, and strict `response_format`
- router input payloads include the constrained template summaries and exact-image-count constraint when present
- exactly one repair retry occurs when the first router response fails validation
- deterministic escalation from `gpt-5.4-mini` to `gpt-5.4` updates the authoritative plan and usage counters

## Extension notes for the next slices

- TG4 should reuse `state["plan"]`, `state["templates"]`, and `state["plan_raw"]` instead of re-calling the router.
- Later nodes should continue to build on DAO methods only, without embedding raw SQL in nodes.
- Nodes should consume `Deps` instead of reading global state or environment variables directly.
- New runtime behavior should continue to add narrow, direct unit tests before broader graph tests.
