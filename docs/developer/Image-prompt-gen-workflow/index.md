# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG8 mocked-validation and documentation closeout slice in progress after TG7 completion
- Last updated: 2026-04-23

## Scope of this slice

This slice now covers the shipped TG1-TG7 implementation plus the first TG8 closeout cluster:

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
- `comicbook.nodes.ingest` for normalizing run input into the initial `RunState` boundary
- `comicbook.nodes.summarize` for deriving final counters, run status, and persisted `runs`-table finalization
- `comicbook.execution` for reusable node binding, run-state preparation, lock acquisition, and crash finalization helpers that multiple graph entry points can share
- `comicbook.input_file` for strict JSON/CSV prompt-file parsing, validation, duplicate detection, and record normalization ahead of batch execution
- `comicbook.repo_protection` for git-backed detection of protected reference-file edits under `ComicBook/DoNotChange/`
- `comicbook.graph` for the ordered LangGraph assembly plus the current library entry point for the full workflow runtime
- `examples.single_portrait_graph` for an alternate one-image graph that reuses shared modules without importing `comicbook.graph` or `comicbook.run`
- `.pre-commit-config.yaml` plus `ComicBook/scripts/check_do_not_change.py` for the repo-local hook that runs the protection check through `uv`
- `ComicBook/README.md` for package-local setup, CLI usage, output locations, and operator guidance

TG7 is now complete. TG8 has started with the full mocked validation rerun, acceptance-evidence mapping, and README usage guidance. Remaining work is limited to the explicitly opt-in live-smoke evidence and final readiness sign-off.

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

### `comicbook.nodes.ingest`

This node now defines the first in-graph state boundary for TG6.

Current behavior:

- requires `state["user_prompt"]`
- preserves a caller-provided `run_id` and `started_at` when present, otherwise fills them from `deps.uuid_factory()` and `deps.clock()`
- normalizes default workflow flags for `dry_run`, `force_regenerate`, `budget_usd`, `exact_image_count`, and `redact_prompts`
- initializes `usage`, `errors`, `image_results`, and `rate_limit_consecutive_failures` so later nodes can append state predictably

### `comicbook.nodes.summarize`

This node now defines the terminal TG6 summary and reporting boundary.

Current behavior:

- requires `state["run_id"]` and `state["started_at"]`
- derives terminal counters from `state["cache_hits"]` and `state["image_results"]`
- marks the run as `failed` when the runtime budget guard blocked image generation before the serial loop started
- marks the run as `succeeded` when all planned prompts were cache hits or generated successfully
- marks the run as `partial` when any prompt failed or was skipped by the rate-limit circuit breaker
- writes `runs/<run_id>/report.md` from the persisted plan, rendered prompts, image results, and summary counts
- writes `logs/<run_id>.summary.json` with the structured run summary, usage, errors, and per-prompt statuses
- hashes prompt text in both artifacts when `state["redact_prompts"]` is true
- persists the final `runs` row counters, router metadata, plan JSON, and lock release via `deps.db.finalize_run(...)`
- returns `ended_at`, `summary`, and `run_status` back into graph state

### `comicbook.execution`

This shared runtime helper module was added in the first TG7 slice so alternate graphs can reuse the same execution contract without importing the workflow-specific `comicbook.graph` module.

Current public helpers:

- `bind_node(node, deps)` binds a shared `Deps` container into any LangGraph node
- `prepare_initial_state(initial_state, deps)` normalizes caller input through the shared ingest boundary before lock acquisition
- `run_graph_with_lock(initial_state, deps, graph_factory=...)` acquires the SQLite run lock, invokes an arbitrary compiled graph, and safely finalizes failed runs when exceptions escape before summary completion
- `format_timestamp(...)` and `pid_is_alive(...)` keep the runtime bookkeeping behavior shared and deterministic across entry points

### `comicbook.graph`

This module now owns the complete TG6 workflow orchestration path for the primary workflow runtime while delegating shared execution concerns to `comicbook.execution`.

Current public helpers:

- `build_workflow_graph(deps)` compiles the ordered graph sequence
- `runtime_gate(state, deps)` estimates remaining image cost, applies the per-run and daily budget guards, and records a workflow error when generation is blocked
- `run_workflow(initial_state, deps)` invokes the primary workflow graph through the reusable execution helper

Current graph order:

1. `ingest`
2. `load_templates`
3. `router`
4. `persist_template`
5. `cache_lookup`
6. `runtime_gate`
7. conditional branch: `summarize` for dry-run or budget-blocked runs, otherwise `generate_images_serial`
8. `summarize`

Current scope boundary:

- dry-run and budget overflow now short-circuit before image generation while still reaching the shared summary node
- report artifacts are emitted from the summary boundary so the graph remains the authoritative source of run outputs

### `comicbook.run`

This module now provides the workflow-specific CLI and test-friendly library entry point required by TG6.

Current public helpers:

- `parse_args(argv)` supports exactly one prompt source: positional `user_prompt` or `--input-file`, plus `--run-id`, `--dry-run`, `--force`, `--panels`, `--budget-usd`, and `--redact-prompts`
- `run_once(...)` maps runtime arguments into the initial `RunState`, loads config and dependencies when needed, and delegates execution to `comicbook.graph.run_workflow(...)`
- `run_batch(...)` executes validated input-file records serially, pre-resolves per-record `run_id` values, and returns a batch summary JSON-ready payload
- `main(argv)` executes either one CLI run or one validated serial batch and prints the corresponding JSON status payload

Locked runtime behaviors now in place:

- `--run-id` is rejected in `--input-file` mode
- the graph and `RunState` remain single-prompt
- file validation completes before the first record runs
- batch mode reuses one managed dependency set per CLI invocation and preserves per-record artifact paths

### `comicbook.input_file`

This module owns the new prompt-file boundary for the CLI batch wrapper.

Current responsibilities:

- validate supported file extensions as `.json` or `.csv`
- parse UTF-8 JSON arrays of strict input-record objects
- parse UTF-8 or BOM-prefixed CSV files with `user_prompt` and optional `run_id` columns
- trim prompt and run-ID strings
- reject blank prompts, blank run IDs, duplicate run IDs, unsupported fields, and unsupported columns
- return validated `InputPromptRecord` values in file order for later serial execution

### `examples.single_portrait_graph`

This example proves the reusable-module boundary required by TG7.

Current behavior:

- assembles an alternate LangGraph topology locally under `examples/` rather than inside `comicbook.graph`
- reuses `comicbook.nodes.ingest`, `load_templates`, `router`, `persist_template`, `cache_lookup`, `generate_images_serial`, and `summarize`
- inserts a local `enforce_single_portrait` node that pins `exact_image_count=1` before router planning
- executes through `comicbook.execution.run_graph_with_lock(...)` so lock handling and crash finalization remain shared runtime behavior
- does not depend on `comicbook.run` or import the workflow-specific `comicbook.graph` module

## Local setup

1. Work from `ComicBook/`.
2. Copy values from `../workflows/.env.example` into a local `.env` in `ComicBook/`, or export the same values in the shell.
3. Use `uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q` for the current full mocked suite, or narrow the path list during TDD.
4. See `ComicBook/README.md` for the documented CLI, library, artifact-location, and operator-usage examples.

## TG8 validation status

Latest recorded mocked regression evidence:

- command: `uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q`
- result: `70 passed`

Acceptance-check evidence currently mapped:

- CLI entry point and runtime flags: `tests/test_budget_guard.py`, `tests/test_input_file_support.py`, `comicbook/run.py`
- input-file parsing, batch ordering, and batch exit semantics: `tests/test_input_file_support.py`, `comicbook/input_file.py`, `comicbook/run.py`
- serial image execution with `n=1`: `tests/test_image_client.py`, `tests/test_node_generate_images_serial.py`
- cache-hit reuse without new image calls: `tests/test_graph_cache_hit.py`
- dry-run reporting without image generation: `tests/test_budget_guard.py`
- same-run resume behavior: `tests/test_graph_resume.py`
- router repair and escalation: `tests/test_router_node.py`, `tests/test_router_validation.py`
- direct node coverage independent of `graph.py`: per-node test files under `ComicBook/tests/`
- reusable alternate graph proof: `tests/test_example_single_portrait.py`
- read-only reference-file protection: `tests/test_repo_protection.py`
- report and summary artifacts: `tests/test_graph_new_template.py`, `tests/test_budget_guard.py`, `comicbook/nodes/summarize.py`

Remaining TG8 validation gap:

- one documented live Azure smoke run still needs explicit opt-in before it can be executed and recorded

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

`ComicBook/tests/test_input_file_support.py` now verifies:

- prompt-source exclusivity for positional prompts vs. `--input-file`
- rejection of `--run-id` in file mode
- JSON input-file parsing, trimming, and duplicate-ID validation
- CSV input-file parsing, column validation, and blank-prompt rejection
- serial batch execution order and uniform forwarding of global runtime flags
- non-zero batch exit behavior when any record finishes `partial` or `failed`

`ComicBook/tests/test_router_validation.py` now verifies:

- valid router payload parsing into `RouterPlan`
- rationale leak redaction
- rejection of unknown prompt template IDs
- acceptance of a router-selected new template ID when the same response defines that extracted template
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

`ComicBook/tests/test_graph_happy.py` now verifies:

- the minimal library entry point acquires the run lock, executes the graph in order, and generates multiple images successfully
- the final `runs` row is persisted with `status="succeeded"`, counters, and cleared lock ownership

`ComicBook/tests/test_graph_cache_hit.py` now verifies:

- a repeated run with the same rendered prompt reuses the persisted image as a cache hit
- the second run performs zero image API calls while still finalizing a successful run summary

`ComicBook/tests/test_graph_resume.py` now verifies:

- a same-run output file on disk is treated as a resumed success inside the full graph path
- only the missing image is sent to Azure during resume, while the final run still succeeds

`ComicBook/tests/test_graph_new_template.py` now verifies:

- the full graph persists exactly one router-extracted template row before prompt composition continues
- report and summary artifacts are still emitted on the extracted-template path

`ComicBook/tests/test_budget_guard.py` now verifies:

- per-run budget overflow stops before any image API call and finalizes the run as failed
- daily budget overflow also stops before any image API call
- `run_once(..., dry_run=True)` writes report artifacts, redacts prompt text, and skips image generation
- `run_once(..., panels=N)` forwards the exact-image-count constraint into the router input and executes the matching prompt count
- `parse_args(...)` accepts the required TG6 runtime flags

`ComicBook/tests/test_example_single_portrait.py` now verifies:

- the alternate example graph runs end to end with mocked HTTP while forcing exactly one planned image
- the router input for the example graph is constrained to `exact_image_count=1` even when the caller supplied a different value
- shared package modules do not import the workflow-specific `comicbook.graph` or `comicbook.run` modules

`ComicBook/tests/test_repo_protection.py` now verifies:

- clean repositories pass the protection check without false positives
- unstaged edits under `ComicBook/DoNotChange/` make the CLI protection check fail
- staged edits under `ComicBook/DoNotChange/` are also detected so the pre-commit hook blocks those commits

`ComicBook/tests/test_node_ingest_summarize.py` now verifies:

- `comicbook.nodes.ingest` can normalize runtime defaults directly, without going through `graph.py`
- `comicbook.nodes.summarize` can write artifacts and finalize the persisted run record directly, without going through `graph.py`

## Extension notes for the next slices

- TG6 and TG7 are complete; later work should keep reusable execution concerns in `comicbook.execution` instead of duplicating them across example or production graphs.
- Later nodes should continue to build on DAO methods only, without embedding raw SQL in nodes.
- Nodes should consume `Deps` instead of reading global state or environment variables directly.
- The repository protection hook should continue to point at `uv run --project ComicBook python ComicBook/scripts/check_do_not_change.py` so it does not depend on a bare `python` binary being present on `PATH`.
- New runtime behavior should continue to add narrow, direct unit tests before broader graph tests.
