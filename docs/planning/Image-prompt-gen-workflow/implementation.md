# Technical Implementation Guide: Image Prompt Generation Workflow

**Status:** Draft for implementation
**Date:** 2026-04-23
**Source:** `docs/planning/Image-prompt-gen-workflow/plan.md`
**Audience:** implementation team
**Authority:** This is the execution document for delivery. If this document conflicts with `plan.md`, this document wins for implementation sequencing, module boundaries, and acceptance expectations.

---

## 1. Purpose

This document translates the approved workflow plan into a single, standalone implementation guide that an engineering team can execute without needing to infer missing details from `plan.md`.

Use this document for:

- repository layout
- module boundaries
- runtime contracts
- database schema and persistence behavior
- router and image-generation behavior
- test requirements
- implementation order
- task grouping and delivery dependencies

Do not use this document for product brainstorming or alternative architecture exploration. Those belong in `plan.md` or a future ADR.

---

## 2. Scope

This v1 implementation delivers a local Python workflow that:

- accepts a free-form prompt
- loads stored style templates from SQLite
- asks a router LLM for a structured generation plan
- optionally persists a newly extracted template
- deterministically builds final image prompts
- deduplicates by prompt fingerprint
- generates uncached images serially, one image API call at a time
- writes outputs, run records, and operator-friendly reports to disk
- supports resume after interruption using persisted state and output files

This v1 does **not** deliver:

- a web UI
- a REST service
- parallel image generation
- multimodal image input
- vector retrieval
- image editing / inpainting
- garbage collection of old generated images

---

## 3. Locked Decisions

The source plan contains a few deliberate tradeoff discussions and a small number of contradictions. The following decisions are locked for implementation and should not be re-opened during build unless a blocker is found.

### 3.1 Execution model

- Image generation is strictly serial.
- Only one image request may be in flight at a time.
- Every image request uses `n=1`.
- No concurrency knob is exposed in v1.

### 3.2 Router call policy

- The main router path starts with `COMICBOOK_ROUTER_MODEL_FALLBACK`, default `gpt-5.4-mini`.
- The router schema includes `needs_escalation: bool` and optional `escalation_reason: str | null`.
- If the first valid plan sets `needs_escalation=true` and the current model is `gpt-5.4-mini`, the workflow performs one second router call on `gpt-5.4` with the same input and uses the second plan as authoritative.
- Schema repair is separate from escalation. A repair retry does not count as an escalation.
- The earlier statement in `plan.md` that the router is called exactly once is superseded by this section.

### 3.3 Template behavior

- Templates are append-only.
- Existing template rows are never mutated in place.
- Duplicate inserts are ignored using `(name, style_text_hash)`.
- Future template revisions create a new row with `supersedes_id` pointing to the previous row.

### 3.4 One-run-at-a-time database policy

- Only one active workflow run may execute against a given SQLite database file at a time.
- A startup lock check is required before graph execution begins.
- A stale lock may be recovered only if the recorded PID is no longer alive on the same host.

### 3.5 Budget and cost guards

- The CLI exposes `--budget-usd`.
- The process also honors `COMICBOOK_DAILY_BUDGET_USD`.
- If the estimated run cost exceeds a configured budget, the run terminates before image generation.

### 3.6 Template pre-filtering

- If stored templates count is `<= 30`, send all template summaries to the router.
- If stored templates count is `> 30`, pre-filter deterministically before the router call.
- v1 pre-filter is lexical only: score templates by case-insensitive overlap between prompt tokens and template `name`, `tags`, and `summary`.
- Pass the top 15 templates by score. Break ties by newest `created_at`, then by `id`.
- If all scores are zero, pass the newest 15 templates.

### 3.7 Reporting artifacts

- Human-readable report path: `runs/<run_id>/report.md`
- Structured run summary path: `logs/<run_id>.summary.json`
- Failure trace path: `logs/<run_id>.log`

### 3.8 Reference scripts policy

- Files under `ComicBook/DoNotChange/` are read-only.
- New code may copy patterns from those scripts but must not import mutable behavior from them except for study/reference.
- A repository protection check must fail if those files are modified.

---

## 4. End-to-End Flow

The implemented workflow must execute in the following order:

1. Parse CLI or library input.
2. Load configuration and validate required secrets.
3. Open SQLite, enable WAL mode, and acquire the single-run lock.
4. Initialize a `runs` row with `status='running'`.
5. Normalize run input into `RunState`.
6. Load and optionally pre-filter template summaries.
7. Call the router model.
8. Validate router output against the schema.
9. If validation fails, perform one repair attempt.
10. If the valid plan requests escalation, re-run the router once on the stronger model.
11. Persist any new template before prompt materialization.
12. Build deterministic `rendered_prompt` strings.
13. Compute fingerprints and partition prompts into cache hits vs. prompts to generate.
14. If `--dry-run`, stop after writing the plan and report artifacts.
15. If budget checks fail, stop before image generation.
16. Iterate over `to_generate` in order and call the image API serially.
17. Save each successful image to disk and persist image metadata.
18. Record failures without aborting the remaining serial loop.
19. Write summary metrics, report artifacts, and final run status.
20. Release the run lock.

---

## 5. Repository Layout

The implementation team should create and maintain the following layout.

```text
ComicBook/
  DoNotChange/
    hello_azure_openai.py
    generate_image_gpt_image_1_5.py
  comicbook/
    __init__.py
    config.py
    deps.py
    state.py
    db.py
    pricing.json
    fingerprint.py
    router_prompts.py
    router_llm.py
    image_client.py
    graph.py
    run.py
    nodes/
      __init__.py
      ingest.py
      load_templates.py
      router.py
      persist_template.py
      cache_lookup.py
      generate_images_serial.py
      summarize.py
  examples/
    single_portrait_graph.py
  seeds/
    .gitkeep
  tests/
    test_config.py
    test_db.py
    test_fingerprint.py
    test_router_validation.py
    test_router_node.py
    test_node_load_templates.py
    test_node_cache_lookup.py
    test_image_client.py
    test_node_generate_images_serial.py
    test_graph_happy.py
    test_graph_cache_hit.py
    test_graph_new_template.py
    test_graph_resume.py
    test_budget_guard.py
    test_example_single_portrait.py
  runs/
  logs/
  image_output/
  .env.example
  .gitignore
  pyproject.toml
```

Only `graph.py` and `run.py` are workflow-specific orchestration files. All other modules should be reusable by a future graph.

---

## 6. Runtime Contracts

### 6.1 Node contract

Every graph node must follow this shape:

```python
def node_name(state: RunState, deps: Deps) -> dict:
    """Return a partial state delta."""
```

Rules:

- Read only from `state` and `deps`.
- Return only the fields changed by the node.
- Do not read module-level globals for runtime data.
- Do not perform hidden side effects outside explicit `deps` collaborators.
- Keep one responsibility per node file.

### 6.2 Shared dependencies

`Deps` must be a frozen dataclass containing explicit runtime dependencies.

Required fields:

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

Optional fields for tests:

- fake router transport
- fake image transport
- fake filesystem abstraction if needed

### 6.3 State model

Implement `RunState` as a typed model boundary. `TypedDict` is acceptable for graph state, but use Pydantic models for structured payload validation.

Required state keys by phase:

| Phase | Required keys |
|---|---|
| Ingest | `run_id`, `user_prompt`, `dry_run`, `force_regenerate`, `started_at` |
| Template load | `templates`, `template_catalog_size`, `templates_sent_to_router` |
| Router | `router_model`, `plan`, `plan_raw`, `plan_repair_attempts`, `router_escalated` |
| Prompt build | `rendered_prompts`, `rendered_prompts_by_fp`, `cache_hits`, `to_generate` |
| Image generation | `image_results`, `errors`, `rate_limit_consecutive_failures` |
| Summary | `usage`, `ended_at`, `summary`, `run_status` |

### 6.4 Pydantic models

Implement at minimum:

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

`RouterPlan` must contain:

- `router_model_chosen: Literal["gpt-5.4", "gpt-5.4-mini"]`
- `rationale: str`
- `needs_escalation: bool = False`
- `escalation_reason: str | None = None`
- `template_decision: RouterTemplateDecision`
- `prompts: list[PromptPlanItem]`

---

## 7. Database Design

### 7.1 SQLite requirements

- Use SQLite in WAL mode.
- Use parameterized queries only.
- Open one shared DB connection per process.
- Keep schema creation idempotent.
- Prefer explicit DAO methods over inline SQL in nodes.

### 7.2 Tables

The implementation must create the following tables.

```sql
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
```

### 7.3 Daily rollup view

Create a view for operator summary metrics.

```sql
CREATE VIEW IF NOT EXISTS daily_run_rollup AS
SELECT
    substr(started_at, 1, 10) AS run_date,
    COUNT(*) AS total_runs,
    SUM(cache_hits) AS total_cache_hits,
    SUM(generated) AS total_generated,
    SUM(failed) AS total_failed,
    SUM(est_cost_usd) AS total_est_cost_usd,
    CASE
        WHEN SUM(cache_hits) + SUM(generated) = 0 THEN 0.0
        ELSE CAST(SUM(cache_hits) AS REAL) / CAST(SUM(cache_hits) + SUM(generated) AS REAL)
    END AS cache_hit_rate
FROM runs
GROUP BY substr(started_at, 1, 10);
```

### 7.4 Required DAO methods

`db.py` must expose methods for:

- schema initialization
- WAL configuration
- run lock acquisition and release
- stale lock detection
- run creation and finalization
- template summary listing
- template full-text lookup by IDs
- template insert with dedup
- prompt upsert-if-absent by fingerprint
- prompt lookup by fingerprint
- image result insert
- existing image lookup by fingerprint
- budget rollup lookup for the current day

Nodes must not execute ad hoc SQL directly.

---

## 8. Configuration and Environment

### 8.1 Required environment variables

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_CHAT_DEPLOYMENT` or equivalent router deployment mapping
- `AZURE_OPENAI_IMAGE_DEPLOYMENT`

### 8.2 Workflow-specific environment variables

- `COMICBOOK_DB_PATH=./comicbook.sqlite`
- `COMICBOOK_IMAGE_OUTPUT_DIR=./image_output`
- `COMICBOOK_RUNS_DIR=./runs`
- `COMICBOOK_LOGS_DIR=./logs`
- `COMICBOOK_ROUTER_MODEL_FALLBACK=gpt-5.4-mini`
- `COMICBOOK_ROUTER_MODEL_ESCALATION=gpt-5.4`
- `COMICBOOK_DAILY_BUDGET_USD=` optional
- `COMICBOOK_ROUTER_PROMPT_VERSION=ROUTER_SYSTEM_PROMPT_V2`
- `COMICBOOK_ENABLE_ROUTER_PREFLIGHT=0`

### 8.3 CLI flags

`run.py` must support:

- positional `user_prompt`
- `--run-id`
- `--dry-run`
- `--force`
- `--panels N`
- `--budget-usd X`
- `--redact-prompts`

Behavior:

- `--run-id` is required for resume testing but optional during normal runs.
- `--force` bypasses cache lookup only for image generation. It does not suppress prompt persistence or run logging.
- `--panels N` becomes `constraints.exact_image_count` in the router input.
- `--redact-prompts` hashes prompt text in logs and reports, but not in the prompts table.

---

## 9. Router Design

### 9.1 Router input

The router receives a single JSON payload containing:

- `user_prompt`
- `known_templates`
- `constraints`
- `available_router_models`

`known_templates` entries contain only:

- `id`
- `name`
- `tags`
- `summary`

Never send full `style_text` values to the router in v1.

### 9.2 Router schema rules

Validation rules:

- `prompts` count must be between 1 and 12 unless `--panels N` is set, in which case the count must equal `N`
- template IDs in prompt items must exist in the selected subset or match the new template ID created in the same response
- `new_template.id` must be a lowercase slug
- `rationale` length must be `<= 600`
- `subject_text` must not be empty and must be subject-focused, not style-only

### 9.3 Repair logic

If schema validation fails:

1. record the raw response
2. build a repair prompt that includes the validation error
3. call the same model once more
4. validate again
5. fail the run if still invalid

Only one repair attempt is allowed.

### 9.4 Rationale leak guard

Before persisting the final plan:

- truncate `rationale` to 600 chars
- compare it against the first 40 chars of `ROUTER_SYSTEM_PROMPT_V2`
- if the rationale contains that substring, replace the rationale with `[redacted: potential prompt-leak]`

### 9.5 Prompt materialization

The router does **not** return final `rendered_prompt` strings.

The application constructs them deterministically:

```python
style_block = "\n\n".join(selected_template.style_text for selected_template in ordered_templates)
rendered_prompt = f"{style_block}\n\n---\n\n{subject_text}" if style_block else subject_text
```

Template order rules:

- preserve the order supplied in each plan item
- if the new template is referenced, resolve it as if it were already part of the template library

---

## 10. Fingerprinting, Caching, and Resume

### 10.1 Fingerprint formula

```text
sha256(rendered_prompt || size || quality || image_model)
```

### 10.2 Cache lookup behavior

For each rendered prompt:

1. compute fingerprint
2. ensure a `prompts` row exists
3. if `--force` is false and a successful image already exists for that fingerprint, classify as cache hit
4. otherwise append to `to_generate`

### 10.3 Resume behavior

Resume is determined by both the database and the filesystem.

For each fingerprint in `to_generate`:

- if `image_output/<run_id>/<fingerprint>.png` already exists, record a resumed success and skip the API call
- otherwise continue to generation

Do not delete failed rows during resume.

### 10.4 Force behavior

`--force` means:

- ignore successful prior image rows during cache classification
- still reuse existing prompt fingerprints
- still persist new run metadata
- still skip an existing file for the same `run_id` during a resume of that exact run to avoid overwriting a completed artifact mid-resume

---

## 11. Image Client Design

### 11.1 Reusable client contract

`image_client.py` must expose a reusable single-image function.

```python
async def generate_one(
    *,
    prompt: str,
    size: str,
    quality: str,
    image_model: str,
    out_path: Path,
) -> ImageClientResult:
    ...
```

Rules:

- one prompt per request
- `n=1` pinned internally
- caller cannot override `n`
- create parent directories before writing
- return structured success/failure metadata
- do not depend on LangGraph or SQLite

### 11.2 Retry policy

- retry on HTTP `408`, `429`, and `5xx`
- maximum 3 attempts
- fixed 120-second backoff in v1 to match the approved plan
- do not retry content filter failures
- do not retry other `4xx` responses

### 11.3 Rate-limit circuit breaker

Inside the serial generation node, maintain a count of consecutive prompts that exhausted retries due to `429`.

Behavior:

- after one retry-exhausted `429`, continue to the next prompt
- after two consecutive retry-exhausted `429` prompt failures, stop calling the image API for the remainder of the run
- record the remaining prompts as `status='skipped_rate_limit'`
- mark the run `partial`

---

## 12. Reporting, Logging, and Summary

### 12.1 JSON logs

Every node should emit structured log events with:

- `run_id`
- `node`
- `event`
- `duration_ms`
- `ok`
- optional `error`

Do not log authorization headers.

### 12.2 Human-readable report

`runs/<run_id>/report.md` must contain:

- run metadata
- original user prompt or redacted hash
- router rationale
- router model used and whether escalation occurred
- template decision
- each prompt item in order
- each final rendered prompt in order
- cache-hit vs generated vs failed status for each fingerprint
- generated file paths
- cost estimate summary

### 12.3 Final run status rules

- `succeeded`: all planned images either came from cache or completed successfully
- `partial`: at least one image failed or was skipped, but the workflow reached summary
- `failed`: router/setup/budget/lock failure prevented meaningful completion

---

## 13. Testing Requirements

The implementation is not complete without tests.

### 13.1 Unit tests

Required unit coverage:

- config loading and validation
- fingerprint stability and change sensitivity
- router schema validation
- router repair handling
- template pre-filter ranking
- template dedup and append-only lineage
- cache lookup partitioning
- image client retry behavior
- serial generation ordering
- rate-limit circuit breaker
- budget guard

### 13.2 Node isolation tests

Every file under `comicbook/nodes/` must have at least one direct test that imports the node module and invokes it without importing `graph.py`.

This is a release gate, not a suggestion.

### 13.3 Integration tests

Required graph-level tests:

- happy path with multiple prompts
- repeated run yields cache hits and zero image API calls
- `extract_new` path persists exactly one template row
- resume after mid-run interruption
- `--dry-run` never calls image generation
- `--panels N` constrains output count
- budget overflow stops before image generation

### 13.4 Modularity proof

`examples/single_portrait_graph.py` and `tests/test_example_single_portrait.py` are required deliverables.

The example graph must reuse shared modules without editing them.

---

## 14. Implementation Sequence

TaskGroups are intentionally sequential. A later TaskGroup must not begin until the prior TaskGroup exit criteria are satisfied. Tasks within a TaskGroup may be split across engineers if the shared contract for that group has already been agreed and committed.

### TaskGroup dependency chain

```text
TG1 Foundation
  -> TG2 Persistence and Locking
    -> TG3 Router Planning
      -> TG4 Template Persistence and Cache Partitioning
        -> TG5 Serial Image Execution
          -> TG6 Graph, CLI, and Reporting
            -> TG7 Reuse Proof and Repo Protections
              -> TG8 Final Validation and Documentation Closeout
```

---

## 15. TaskGroups

### TaskGroup 1: Foundation

**Depends on:** none
**Goal:** establish package layout, configuration loading, core state contracts, and project wiring so all later groups can build against stable interfaces.

#### Tasks

1. Create the package skeleton under `ComicBook/comicbook/`, `tests/`, `examples/`, `runs/`, and `logs/`.
2. Add `pyproject.toml` dependencies and pin `langgraph` with `~=`.
3. Implement `config.py` with env-first loading, `.env` fallback, and validation of all required Azure settings.
4. Implement `state.py` Pydantic models and the `RunState` typed contract.
5. Implement `deps.py` with the frozen `Deps` dataclass and test doubles strategy.
6. Add `.env.example` and `.gitignore` entries for `.env`, SQLite artifacts, logs, generated runs, and images.
7. Add baseline unit tests for config and state validation.

#### Files created or updated

- `ComicBook/comicbook/__init__.py`
- `ComicBook/comicbook/config.py`
- `ComicBook/comicbook/state.py`
- `ComicBook/comicbook/deps.py`
- `ComicBook/.env.example`
- `ComicBook/.gitignore`
- `ComicBook/pyproject.toml`
- `ComicBook/tests/test_config.py`

#### Exit criteria

- local import of `comicbook` succeeds
- config validation fails cleanly when secrets are absent
- state models parse and validate known-good payloads
- repository layout matches Section 5

#### Notes for the next group

- No SQLite or router logic should be embedded here.
- Keep these modules generic enough for reuse by the example graph later.

### TaskGroup 2: Persistence and Locking

**Depends on:** TaskGroup 1
**Goal:** create the SQLite schema, DAO, run-lock behavior, and budget rollup support.

#### Tasks

1. Implement schema initialization in `db.py`.
2. Enable WAL mode at startup and expose a DAO initialization path.
3. Implement `runs` lock acquisition, stale lock detection, and lock release.
4. Implement CRUD methods for templates, prompts, images, and run summaries.
5. Create the `daily_run_rollup` SQL view.
6. Add tests for template dedup, append-only lineage support, run lock behavior, and rollup calculations.

#### Files created or updated

- `ComicBook/comicbook/db.py`
- `ComicBook/tests/test_db.py`

#### Exit criteria

- schema init is idempotent
- only one active run can acquire the lock for the same DB
- stale lock recovery is covered by tests
- rollup view returns cache-hit-rate correctly

#### Notes for the next group

- The router implementation must call only DAO methods, not raw SQL.

### TaskGroup 3: Router Planning

**Depends on:** TaskGroup 2
**Goal:** implement router prompts, schema validation, repair handling, template pre-filtering, and the reusable router client.

#### Tasks

1. Implement `router_prompts.py` with `ROUTER_SYSTEM_PROMPT_V2` and the authoritative JSON schema.
2. Add `needs_escalation` and `escalation_reason` to the schema.
3. Implement deterministic template pre-filtering for catalogs larger than 30 entries.
4. Implement `router_llm.py` using the Azure Responses API pattern.
5. Implement validation, repair retry, and rationale leak guard.
6. Implement `nodes/load_templates.py` and `nodes/router.py`.
7. Add unit tests for schema validation, bad template IDs, repair behavior, escalation behavior, and pre-filter ranking.

#### Files created or updated

- `ComicBook/comicbook/router_prompts.py`
- `ComicBook/comicbook/router_llm.py`
- `ComicBook/comicbook/nodes/load_templates.py`
- `ComicBook/comicbook/nodes/router.py`
- `ComicBook/tests/test_router_validation.py`
- `ComicBook/tests/test_router_node.py`
- `ComicBook/tests/test_node_load_templates.py`

#### Exit criteria

- valid router output parses into `RouterPlan`
- exactly one repair attempt occurs on invalid schema output
- escalation to the stronger router model is tested and deterministic
- template catalogs over 30 entries are filtered deterministically

#### Notes for the next group

- Do not compose final rendered prompts inside the router node.
- Persisting a new template belongs to the next group.

### TaskGroup 4: Template Persistence and Cache Partitioning

**Depends on:** TaskGroup 3
**Goal:** persist extracted templates, deterministically compose prompts, compute fingerprints, and partition work into cache hits vs. uncached prompts.

#### Tasks

1. Implement `nodes/persist_template.py` for optional template insertion.
2. Implement `fingerprint.py` for prompt composition and `sha256` fingerprinting.
3. Implement `nodes/cache_lookup.py`.
4. Ensure prompt rows are created before generation begins.
5. Respect `--force` in cache classification without breaking resume semantics.
6. Add tests for fingerprint determinism, duplicate prompts, cache hits, and extracted-template flows.

#### Files created or updated

- `ComicBook/comicbook/fingerprint.py`
- `ComicBook/comicbook/nodes/persist_template.py`
- `ComicBook/comicbook/nodes/cache_lookup.py`
- `ComicBook/tests/test_fingerprint.py`
- `ComicBook/tests/test_node_cache_lookup.py`

#### Exit criteria

- identical rendered inputs produce identical fingerprints
- any size, quality, model, or text change alters the fingerprint
- cache hits are separated from generation work correctly
- extracted templates are persisted before prompt composition

#### Notes for the next group

- `to_generate` ordering must remain identical to router output ordering.

### TaskGroup 5: Serial Image Execution

**Depends on:** TaskGroup 4
**Goal:** implement the reusable image client and the serial generation node with retry, resume, and circuit-breaker behavior.

#### Tasks

1. Implement `image_client.py` as a reusable single-image client.
2. Implement `nodes/generate_images_serial.py`.
3. Add content-filter handling and terminal failure recording.
4. Add resume logic based on existing output files for the same `run_id`.
5. Add the two-consecutive-429 circuit breaker.
6. Persist image success and failure rows.
7. Add unit tests for retry behavior, failure handling, serial ordering, and circuit breaking.

#### Files created or updated

- `ComicBook/comicbook/image_client.py`
- `ComicBook/comicbook/nodes/generate_images_serial.py`
- `ComicBook/tests/test_image_client.py`
- `ComicBook/tests/test_node_generate_images_serial.py`

#### Exit criteria

- image calls are provably serial in tests
- every request uses `n=1`
- the node continues after a single prompt failure
- the node stops remaining API calls after two consecutive retry-exhausted `429` prompt failures

#### Notes for the next group

- Summary/reporting logic must consume `ImageResult` records rather than infer status from the filesystem.

### TaskGroup 6: Graph, CLI, and Reporting

**Depends on:** TaskGroup 5
**Goal:** assemble the workflow graph, expose the CLI and library entry points, implement reports, summaries, and budget guards.

#### Tasks

1. Implement `nodes/ingest.py` and `nodes/summarize.py`.
2. Implement `graph.py` wiring with the ordered node sequence from Section 4.
3. Implement `run.py` CLI parsing and library callable entry point.
4. Implement `--dry-run`, `--panels`, `--budget-usd`, `--run-id`, and `--redact-prompts` behavior.
5. Implement run summary persistence and final `runs` status updates.
6. Implement `runs/<run_id>/report.md` and `logs/<run_id>.summary.json` generation.
7. Add integration tests for happy path, cache-hit path, resume path, dry-run path, budget overflow, and exact panel counts.

#### Files created or updated

- `ComicBook/comicbook/nodes/ingest.py`
- `ComicBook/comicbook/nodes/summarize.py`
- `ComicBook/comicbook/graph.py`
- `ComicBook/comicbook/run.py`
- `ComicBook/tests/test_graph_happy.py`
- `ComicBook/tests/test_graph_cache_hit.py`
- `ComicBook/tests/test_graph_new_template.py`
- `ComicBook/tests/test_graph_resume.py`
- `ComicBook/tests/test_budget_guard.py`

#### Exit criteria

- CLI works for dry-run and normal execution
- run reports are written to disk
- budget overflow stops before any image call
- `--panels N` is enforced end-to-end

#### Notes for the next group

- The example graph must import reusable modules only; it must not depend on `run.py` or internal CLI behavior.

### TaskGroup 7: Reuse Proof and Repo Protections

**Depends on:** TaskGroup 6
**Goal:** prove the reusable-module design and protect read-only reference assets.

#### Tasks

1. Implement `examples/single_portrait_graph.py` using shared modules only.
2. Add `tests/test_example_single_portrait.py` to prove the alternate graph works.
3. Add a repo protection hook or CI check that fails when `ComicBook/DoNotChange/` files are modified.
4. Verify no shared module imports `graph.py` or `run.py`.
5. Add any missing node-isolation tests required for modularity enforcement.

#### Files created or updated

- `ComicBook/examples/single_portrait_graph.py`
- `ComicBook/tests/test_example_single_portrait.py`
- `.pre-commit-config.yaml` or equivalent CI/protection script

#### Exit criteria

- alternate graph runs with mocked HTTP
- reference scripts remain byte-identical
- all node files have direct tests independent of `graph.py`

#### Notes for the next group

- The final group is release hardening and documentation closeout, not new feature work.

### TaskGroup 8: Final Validation and Documentation Closeout

**Depends on:** TaskGroup 7
**Goal:** complete readiness checks, document operational use, and verify that all acceptance criteria are satisfied.

#### Tasks

1. Run the full mocked test suite and capture the command and result in implementation notes.
2. Perform one documented live smoke test behind an explicit opt-in flag.
3. Verify acceptance criteria from Section 16 one by one.
4. Create or update README usage instructions.
5. Update workflow-specific business and developer documentation to match the shipped behavior.
6. Record any deviations from this implementation guide in a follow-up ADR or change note.

#### Files created or updated

- `ComicBook/README.md`
- workflow-specific docs under `docs/business/` and `docs/developer/`
- any release checklist artifacts

#### Exit criteria

- mocked tests pass
- one live smoke test result is documented
- docs reflect the implemented behavior
- no open blocker remains against the v1 acceptance checklist

---

## 16. Acceptance Checklist

The implementation is considered complete only when all items below are true.

- `python -m comicbook.run "<prompt>"` produces images under `image_output/<run_id>/`.
- A `runs` row is written with the correct terminal status.
- Image generation is observably serial and always uses `n=1`.
- Re-running the same prompt without `--force` produces cache hits and zero new image API calls.
- `--dry-run` produces a plan and report without calling the image API.
- Resuming with the same `--run-id` generates only the missing images.
- Router schema failures trigger exactly one repair attempt.
- Router escalation behavior is covered by tests.
- Every node module has at least one direct unit test that does not import `graph.py`.
- `examples/single_portrait_graph.py` works without modifying the reusable modules.
- `ComicBook/DoNotChange/` files are unchanged.
- Budget guards prevent image generation when the budget would be exceeded.
- Human-readable and structured summary artifacts are written to disk.

---

## 17. Open Issues That Are Explicitly Deferred

Do not expand v1 scope to include the following unless a separate change is approved.

- `--exclude-templates`
- multimodal input
- quality-scoring loop
- PII detection preprocessor
- automated image garbage collection
- parallel image generation

---

## 18. Implementation Notes for the Team

### 18.1 Minimality rules

- Keep shared helpers small and reusable.
- Do not add abstraction layers without a direct reuse reason.
- Prefer pure helper functions over manager classes where possible.
- Keep graph topology in `graph.py`; keep domain logic out of it.

### 18.2 Failure-handling rules

- Router/setup failures fail the run.
- Image failures do not fail the entire run unless the process cannot continue at all.
- Retry logic belongs in the client layer; continuation logic belongs in the serial generation node.

### 18.3 Auditability rules

- Persist the final validated plan JSON.
- Persist the router prompt version.
- Persist enough metadata to explain why a prompt was cached, generated, failed, or skipped.

### 18.4 What not to do

- Do not mutate template rows in place.
- Do not batch image generation.
- Do not let nodes talk directly to other nodes.
- Do not let reusable modules import CLI-only code.
- Do not modify the `DoNotChange/` scripts.

---

## 19. Handoff Summary

Implementation should begin with TaskGroup 1 and proceed in order through TaskGroup 8. No team should start a later TaskGroup before the prior TaskGroup exit criteria are met. If a deviation is required during implementation, update this document before proceeding so it remains the single source of execution truth.
