# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG5 complete, covering image-client transport and serial image execution on top of TG4 prompt preparation
- Last updated: 2026-04-23

## Scope of this slice

This slice now covers the TG1-TG3 foundation, the full TG4 cache-preparation boundary, and the first complete TG5 serial-image-execution boundary:

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
- `comicbook.nodes.persist_template` for writing router-extracted templates before prompt composition and normalizing duplicate-template references onto the canonical stored template ID
- `comicbook.fingerprint` for deterministic rendered-prompt composition and `sha256` fingerprint calculation
- `comicbook.nodes.cache_lookup` for prompt materialization, prompt-row persistence, duplicate-fingerprint collapse, and cache-hit classification
- `comicbook.image_client` for reusable single-image Azure generation with `n=1`, bounded retry behavior, and structured success or terminal-failure metadata
- `comicbook.nodes.generate_images_serial` for ordered image execution, same-run resume detection, per-image persistence, and the two-consecutive-429 circuit breaker

It intentionally still does **not** add graph wiring, CLI execution, budget guards, or reporting artifacts yet.

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

### `comicbook.nodes.persist_template`

The persist-template node is the first TG4 execution step after the router plan becomes authoritative.

Current behavior:

- requires `state["plan"]`, `state["templates"]`, and `state["run_id"]`
- no-ops when `plan.template_decision.extract_new_template` is false
- inserts the router-authored `new_template` through `deps.db.insert_template(...)`
- uses `deps.clock()` for the persisted timestamp and `state["run_id"]` as `created_by_run`
- appends a new `TemplateSummary` to `state["templates"]` only when the persisted row is genuinely new to the loaded catalog
- rewrites the in-memory `plan` when insert deduplication returns an existing template row with a different canonical ID

Dedup normalization matters because later prompt composition must resolve every `template_id` through `deps.db.get_templates_by_ids(...)`. If the router proposed `new_template.id="foo"` but the DAO reused an existing row `bar`, the node rewrites prompt references from `foo` to `bar` and collapses accidental duplicates while preserving order.

### `comicbook.fingerprint`

This module now owns deterministic prompt materialization helpers that the later cache-lookup node can reuse directly.

Current public helpers:

- `render_prompt_text(...)` to concatenate ordered template `style_text` blocks with the `---` separator mandated by the implementation guide
- `compute_prompt_fingerprint(...)` to apply the approved `sha256(rendered_prompt || size || quality || image_model)` formula
- `materialize_rendered_prompts(...)` to turn a validated `RouterPlan` plus a resolved `TemplateRecord` lookup into ordered `RenderedPrompt` models with fingerprints attached

Failure behavior:

- prompt materialization raises a clear `ValueError` if any referenced template ID cannot be resolved to a full stored template row

### `comicbook.image_client`

This module now owns the reusable single-image Azure transport contract required by TG5.

Current behavior:

- builds the deployment-scoped image-generation URL under `/openai/deployments/<image_model>/images/generations`
- sends exactly one prompt per request with `n=1`
- writes the decoded `data[0].b64_json` image bytes to the caller-provided output path after creating parent directories
- retries only on `408`, `429`, and `5xx` responses, with a maximum of three attempts
- does not retry content-filter rejections or other terminal `4xx` responses
- returns structured `ImageClientResult` metadata so graph nodes can persist or classify the outcome without parsing transport errors themselves

### `comicbook.nodes.cache_lookup`

This node completes the TG4 prompt-build stage that feeds later image execution.

Current behavior:

- requires `state["plan"]`, `state["templates"]`, `state["run_id"]`, and `state["started_at"]`
- resolves the canonical template IDs in the plan through `deps.db.get_templates_by_ids(...)`
- materializes ordered `RenderedPrompt` items by reusing `comicbook.fingerprint.materialize_rendered_prompts(...)`
- upserts every prompt fingerprint into the `prompts` table before generation begins, even when a prompt is already cached or duplicated within the same run
- builds `rendered_prompts_by_fp` from the first occurrence of each fingerprint so later nodes can process unique work items deterministically
- classifies a prompt as a cache hit only when an existing image row has `status="generated"` and a stored file path
- respects `state.get("force_regenerate", False)` by bypassing cache-hit classification while still reusing the same persisted prompt fingerprint rows

Ordering and duplicate behavior:

- `rendered_prompts` preserves the router-authored prompt order exactly, including duplicate rendered inputs
- `cache_hits` and `to_generate` collapse duplicate fingerprints to one ordered work item each so later image generation does not retry the same fingerprint twice in one run

### `comicbook.nodes.generate_images_serial`

This node now completes the TG5 serial execution boundary that turns TG4 prompt work into persisted image outcomes.

Current behavior:

- requires `state["run_id"]`, `state["to_generate"]`, and `state["rendered_prompts_by_fp"]`
- resolves each queued fingerprint through `rendered_prompts_by_fp` rather than recomputing prompt content
- builds output paths as `deps.output_dir / run_id / <fingerprint>.png`
- treats an existing same-run output file as a resumed success and skips the Azure API call for that fingerprint
- calls `comicbook.image_client.generate_one(...)` strictly serially for remaining prompts, preserving the `to_generate` order exactly
- persists `images` rows for generated, failed, and `skipped_rate_limit` outcomes
- appends structured `ImageResult` and `WorkflowError` entries back into state
- increments `usage.image_calls` by the number of actual Azure request attempts, including retries
- stops the remaining serial loop after two consecutive retry-exhausted `429` prompt failures and records the rest as `skipped_rate_limit`

## Local setup

1. Work from `ComicBook/`.
2. Copy values from `.env.example` into a local `.env` or export them in the shell.
3. Use `uv run --with pytest --with pydantic --with httpx python -m pytest -q tests/test_config.py tests/test_db.py tests/test_router_validation.py tests/test_node_load_templates.py tests/test_router_node.py tests/test_fingerprint.py tests/test_node_cache_lookup.py tests/test_image_client.py tests/test_node_generate_images_serial.py` for the current focused unit-test scope.

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

`ComicBook/tests/test_fingerprint.py` now verifies:

- fingerprint stability for identical rendered inputs
- fingerprint sensitivity when rendered text, size, quality, or model changes
- ordered prompt materialization from ordered template style blocks
- persistence of router-extracted templates before prompt composition occurs
- normalization of duplicate extracted-template IDs onto the canonical stored template row

`ComicBook/tests/test_node_cache_lookup.py` now verifies:

- cache-hit partitioning against previously generated image rows
- duplicate rendered prompts collapse to one ordered generation work item while preserving the full rendered prompt list
- `force_regenerate=True` bypasses cache hits without rewriting prompt fingerprints
- failed image rows do not count as cache hits

`ComicBook/tests/test_image_client.py` now verifies:

- the reusable image client retries a retryable `429` response and still writes the final image bytes to disk
- every request payload pins `n=1` and targets the deployment-scoped image-generation endpoint
- content-filter failures are treated as terminal and are not retried

`ComicBook/tests/test_node_generate_images_serial.py` now verifies:

- same-run resume behavior skips the API call when the output file already exists and still records a generated image result
- non-retryable per-image failures do not abort the remaining serial work
- two consecutive retry-exhausted `429` prompt failures trigger the circuit breaker and mark remaining prompts as `skipped_rate_limit`

## Extension notes for the next slices

- TG6 should assemble the graph and CLI around the existing node boundaries rather than folding transport or persistence logic back into orchestration files.
- Later nodes should continue to build on DAO methods only, without embedding raw SQL in nodes.
- Nodes should consume `Deps` instead of reading global state or environment variables directly.
- New runtime behavior should continue to add narrow, direct unit tests before broader graph tests.
