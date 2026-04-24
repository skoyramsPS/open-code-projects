# Technical Implementation Guide: Template Upload Workflow

**Status:** Draft for implementation  
**Date:** 2026-04-24  
**Source planning document:** `docs/planning/template-upload-workflow/plan.md`  
**Audience:** delivery team  
**Authority:** This is the primary execution document for building the template-upload workflow. Implementation should not require reopening the source planning document except for historical context.

---

## 1. Purpose and scope

This guide defines how to add a second LangGraph workflow to the `ComicBook` package that imports art-style templates from JSON into the existing SQLite template library.

The workflow must:

- accept a JSON file path or stdin payload
- validate and normalize one template row at a time
- optionally backfill missing metadata through the existing Azure Responses transport
- insert new templates or update existing templates in place
- resume safely on rerun using file-hash and row-index tracking
- emit durable run and row audit records plus a markdown report

This guide is intentionally narrower than the planning document. It converts the approved design into a dependency-aware build sequence and resolves the planning document's contradictions so the implementation team has one locked contract.

This change is **significant** at implementation time because it adds a workflow, new persistence tables, new CLI/runtime surfaces, and shared-module changes. The implementation itself will therefore require the full docs gate later. This command, however, is still a **planning-only documentation update**, so only planning docs are changed now.

---

## 2. Current repository baseline

Implementation must fit the code that exists today.

### 2.1 Existing reusable runtime

Current repository modules already provide these reusable building blocks:

- `ComicBook/comicbook/db.py`
  - owns the SQLite schema for `templates`, `prompts`, `images`, and `runs`
  - enables WAL mode and provides the existing run-lock helpers
  - already supports template inserts, prompt persistence, and image-result persistence
- `ComicBook/comicbook/state.py`
  - defines `RunState`, `WorkflowError`, `UsageTotals`, and template-related Pydantic models
- `ComicBook/comicbook/deps.py`
  - defines the shared `Deps` dataclass used by all nodes
- `ComicBook/comicbook/config.py`
  - loads env-first config with `.env` fallback
- `ComicBook/comicbook/router_llm.py`
  - already performs structured Responses API calls and returns input/output token usage
- `ComicBook/comicbook/execution.py`
  - binds nodes and runs a compiled LangGraph with lock acquisition and crash finalization
- `ComicBook/comicbook/graph.py`
  - demonstrates the existing node-binding and graph-compilation pattern
- `ComicBook/comicbook/nodes/`
  - already follows the `fn(state, deps) -> dict` contract expected for new nodes

### 2.2 Repository reality relevant to this change

As of this guide's creation:

- there is **no existing upload workflow implementation** under `ComicBook/comicbook/`
- there are **no upload-specific tests** under `ComicBook/tests/`
- `docs/planning/template-upload-workflow/` contains `plan.md` and `sample_input.json`
- there are **no** workflow-specific business or developer docs yet for `template-upload-workflow`
- `comicbook.__init__` does **not** currently export an `upload_templates` library helper

### 2.3 Stable boundaries that this change must preserve

Implementation must preserve these current behaviors unless this guide explicitly changes them:

- the image-generation workflow remains available at `python -m comicbook.run`
- `DoNotChange/` files remain untouched
- shared runtime helpers keep their existing public behavior for the image workflow
- no new third-party package is introduced
- tests continue to run with `pytest`

---

## 3. Resolved ambiguities and locked decisions

The planning document contains some contradictions and open items. The following decisions are locked for implementation.

### 3.1 CLI module name and package export

The planning document uses both `python -m comicbook.upload_templates` and `python -m comicbook.upload_run`.

**Decision:**

- CLI entry module: `python -m comicbook.upload_run`
- library helper: `upload_templates(...)`
- package re-export: `from comicbook import upload_templates`

Why:

- the repository already uses `run.py` as the executable-style module name
- the planned file layout explicitly names `upload_run.py`
- keeping a library helper separate from the module name gives a clean import surface without adding a second CLI module

Implementation detail:

- define `upload_templates(...)` in `ComicBook/comicbook/upload_run.py`
- re-export it from `ComicBook/comicbook/__init__.py`
- do **not** create a second `upload_templates.py` module

### 3.2 Input envelope format

**Decision:** accept both of these as version-1 inputs:

1. a bare top-level array of template objects
2. an object envelope shaped as `{ "version": 1, "templates": [...] }`

All downstream logic normalizes both forms into the same `raw_rows` list plus an `input_version` marker.

Why:

- this preserves compatibility with the existing `sample_input.json`
- it also creates a forward-compatible expansion point without forcing a breaking change now

### 3.3 When metadata backfill is triggered

The planning document first treats `tags == []` as missing, then later adopts the opposite rule.

**Decision:**

- backfill `tags` only when `tags` is absent or `null`
- preserve `tags: []` as an intentional empty list
- backfill `summary` when `summary` is absent, `null`, or blank after trimming

Why:

- it is the least surprising rule for hand-authored JSON
- it matches the planning document's consolidated adopted change `U4`

### 3.4 Zero-diff updates

The planning document leaves open whether an update with no material changes should be `updated` or something else.

**Decision:** use terminal status `skipped_duplicate` when the incoming row resolves to no persisted changes after normalization.

Rules:

- `skipped_duplicate` is a terminal success status
- it is included in the resume skip set on reruns of the same file hash
- dry-run still uses `dry_run_ok`, even when the would-be diff is empty

Why:

- the status is clearer in reports
- it avoids unnecessary writes to `templates`
- it matches the planning document's preferred resolution for this ambiguity

### 3.5 `supersedes_id` under the real SQLite foreign key

The planning document says missing `supersedes_id` targets should warn but still persist, but the existing `templates.supersedes_id` column already has a foreign-key constraint.

**Decision:** implement a two-phase resolution pass plus safe null fallback.

Rules:

1. first-pass row normalization stores `requested_supersedes_id`
2. if the referenced template already exists, persist it normally
3. if the referenced template is expected later in the same import file, defer final write-mode evaluation for that row until the post-pass resolution step
4. after the post-pass retry:
   - if the target now exists, persist with that `supersedes_id`
   - if the target still does not exist, persist with `supersedes_id = NULL` and record a warning that includes the originally requested id

This preserves the planning intent of not failing the row while staying valid against the current schema.

### 3.6 Import-run locking schema

Section 10 of the planning document assumes `pid` and `host` are tracked on `import_runs`, but the proposed schema omits those columns.

**Decision:** `import_runs` must include `pid` and `host`.

Import lock policy:

- image-generation runs and template-import runs may coexist
- only one import run may be `running` for a given database at a time
- stale import locks are recovered using the same host/pid policy already used for `runs`

### 3.7 Row-result uniqueness and retry history

The planning document proposes `UNIQUE(source_file_hash, row_index, status)` and later adopts a `retry_count` feature. Those two decisions conflict because repeated failures across reruns would collide.

**Decision:** store exactly one terminal row-result per row per import run and keep retry history across runs.

Rules:

- `import_row_results` gets `UNIQUE(import_run_id, row_index)`
- a new `retry_count` column stores the number of prior terminal attempts for the same `(source_file_hash, row_index)` before the current row result is written
- resume lookups query the latest prior results by `source_file_hash` and row index and skip only prior terminal successes `{inserted, updated, skipped_duplicate}`

Why:

- it supports repeated failed retries cleanly
- it keeps one durable row result per row per run
- it makes reporting prior failure count straightforward

### 3.8 Transaction shape

The planning document proposes both per-row atomic commits and optional multi-row batching.

**Decision:** keep one transaction per row in v1.

Each successful write path must commit these changes together:

- template insert or update
- matching `import_row_results` row

Why:

- it gives the cleanest resume semantics
- it matches the current DAO style in `db.py`
- it avoids losing multiple rows of progress on crash

Batch commits are explicitly **out of scope for v1**.

### 3.9 Output directories

The planning document suggests a separate `COMICBOOK_IMPORT_OUTPUT_DIR`, but the current repo already has `runs_dir` and `logs_dir` in `Deps`.

**Decision:** reuse existing output roots.

- import markdown report: `runs/<import_run_id>/import_report.md`
- import structured log: `logs/<import_run_id>.import.jsonl`

Do **not** add a separate import output directory env var in v1.

### 3.10 Budget guard for backfill

**Decision:** add `--budget-usd` support to the upload workflow, but scope it only to estimated LLM backfill spend for the current import run.

- rows that need no backfill can still proceed when budget is `0`
- if estimated cumulative backfill spend would exceed the run budget, remaining rows that still need backfill fail with `budget_exceeded`
- already-persisted rows are not rolled back

---

## 4. Repository impact and module boundaries

### 4.1 Files expected to change

```text
ComicBook/
  comicbook/
    __init__.py                         # update: re-export upload_templates
    config.py                           # update: import-specific guardrail config
    db.py                               # update: import tables, DAO methods, import lock helpers
    state.py                            # update: import TypedDicts / records / statuses
    upload_graph.py                     # new: LangGraph assembly for template import
    upload_run.py                       # new: CLI + library entry point
    metadata_prompts.py                 # new: backfill prompt + schema helpers
    nodes/
      upload_load_file.py              # new
      upload_parse_and_validate.py     # new
      upload_resume_filter.py          # new
      upload_backfill_metadata.py      # new
      upload_decide_write_mode.py      # new
      upload_persist.py                # new
      upload_summarize.py              # new
  tests/
    test_upload_load_file.py           # new
    test_upload_parse_and_validate.py  # new
    test_upload_resume_filter.py       # new
    test_upload_backfill_metadata.py   # new
    test_upload_decide_write_mode.py   # new
    test_upload_persist.py             # new
    test_upload_graph.py               # new
    test_upload_run_cli.py             # new
    test_db.py                         # update: import tables, import lock, DAO additions
    test_config.py                     # update: import config defaults/validation
docs/
  planning/
    template-upload-workflow/
      implementation.md                # this guide
      implementation-handoff.md        # execution status ledger
      index.md                         # planning-folder index
```

### 4.2 Files expected to remain unchanged unless a real gap is discovered

Avoid changing these unless tests prove the guide is incomplete:

- `ComicBook/comicbook/router_prompts.py`
- `ComicBook/comicbook/graph.py`
- `ComicBook/comicbook/execution.py` for the image workflow path
- existing image-workflow nodes unrelated to shared helper reuse
- anything under `ComicBook/DoNotChange/`

### 4.3 Module responsibilities

#### `comicbook/upload_run.py`

Owns entry-layer concerns only:

- CLI parsing
- stdin vs path source selection
- preflight config validation
- construction and lifecycle of managed dependencies
- calling the upload graph
- final stdout summary and exit code
- library helper `upload_templates(...)`

It must not contain row-validation or SQL business logic.

#### `comicbook/upload_graph.py`

Owns graph topology only:

- compiling the upload graph
- routing between nodes
- delegating lock/crash wrapping to execution helpers or a thin import-specific equivalent

#### `comicbook/metadata_prompts.py`

Owns only backfill prompt/schema material:

- system prompt
- JSON schema
- helper to build backfill input payloads

It must not open HTTP clients or call the network.

#### `comicbook/nodes/upload_*.py`

Each node owns one focused state transition and must keep the existing repo contract:

```python
def node_name(state: ImportRunState, deps: Deps) -> dict[str, object]:
    ...
```

No node should depend on module-level mutable globals.

#### Shared modules

- `db.py` remains the only place that owns SQL and persistence helpers
- `state.py` remains the only place that owns stable TypedDict/Pydantic contracts
- `config.py` remains the only place that owns env parsing
- `deps.py` should only change if an already-present dependency slot is insufficient

---

## 5. Runtime contracts

### 5.1 CLI contract

Final CLI surface:

```bash
uv run python -m comicbook.upload_run docs/planning/template-upload-workflow/sample_input.json
uv run python -m comicbook.upload_run --stdin < docs/planning/template-upload-workflow/sample_input.json
uv run python -m comicbook.upload_run --dry-run --no-backfill path/to/templates.json
```

Argument rules:

- one prompt source only:
  - positional `source_file`
  - or `--stdin`
- optional flags:
  - `--dry-run`
  - `--no-backfill`
  - `--allow-missing-optional` (valid only when `--no-backfill` is also set)
  - `--budget-usd <float>`
  - `--redact-style-text-in-logs`
  - `--allow-external-path`
- reject `--allow-missing-optional` without `--no-backfill`

Exit codes:

- `0` success or partial success with at least one row imported/updated/skipped successfully and no hard run failure
- `2` config/preflight error before graph execution
- `3` file-read or JSON-shape hard failure before row processing
- `4` import lock contention
- `5` unhandled workflow failure after run record creation

Note: row-level failures do **not** cause a non-zero exit by themselves. They produce `import_runs.status='partial'` and are reported in stdout/report output.

### 5.2 Library contract

Expose a library helper with one stable surface:

```python
def upload_templates(
    source_file: str | Path | None = None,
    *,
    stdin_text: str | None = None,
    dry_run: bool = False,
    no_backfill: bool = False,
    allow_missing_optional: bool = False,
    allow_external_path: bool = False,
    budget_usd: float | None = None,
    redact_style_text_in_logs: bool = False,
    deps: Deps | None = None,
    dotenv_path: str | Path = ".env",
) -> ImportRunState:
    ...
```

Rules:

- exactly one of `source_file` or `stdin_text` must be provided
- caller receives the final `ImportRunState`
- managed config/DB/http resources are created only when `deps is None`
- the CLI calls this helper instead of duplicating logic

### 5.3 State contract additions in `state.py`

Add import-specific types beside the existing workflow state.

Recommended shape:

```python
ImportRowStatus = Literal[
    "inserted",
    "updated",
    "failed",
    "skipped_resume",
    "skipped_duplicate",
    "dry_run_ok",
]


class TemplateImportRow(TypedDict, total=False):
    row_index: int
    template_id: str | None
    name: str | None
    style_text: str | None
    tags: list[str] | None
    summary: str | None
    created_at: str | None
    requested_supersedes_id: str | None
    resolved_supersedes_id: str | None
    validation_errors: list[str]
    warnings: list[str]
    needs_backfill_tags: bool
    needs_backfill_summary: bool
    backfill_raw: str | None
    write_mode: Literal["insert", "update", "skip", "defer"]
    retry_count: int


class TemplateImportRowResult(TypedDict, total=False):
    row_index: int
    template_id: str | None
    status: ImportRowStatus
    reason: str | None
    warnings: list[str]
    diff: dict[str, dict[str, object]] | None
    retry_count: int


class ImportRunState(TypedDict, total=False):
    import_run_id: str
    source_file_path: str | None
    source_label: str                  # path string or "<stdin>"
    source_file_hash: str
    input_version: int
    dry_run: bool
    no_backfill: bool
    allow_missing_optional: bool
    allow_external_path: bool
    budget_usd: float | None
    redact_style_text_in_logs: bool
    started_at: str
    ended_at: str | None
    raw_rows: list[dict[str, object]]
    parsed_rows: list[TemplateImportRow]
    rows_to_process: list[int]
    deferred_rows: list[int]
    rows_skipped_by_resume: list[int]
    row_results: list[TemplateImportRowResult]
    usage: UsageTotals
    errors: list[WorkflowError]
    run_status: str
    report_path: str | None
```

Implementation note:

- keep import types in the existing `state.py` rather than creating a second state module
- reuse `UsageTotals` and `WorkflowError`

### 5.4 Persistence contract

#### `templates`

Do not change the existing `templates` schema.

#### New `import_runs` table

Use this resolved schema shape:

```sql
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
```

#### New `import_row_results` table

Use this resolved schema shape:

```sql
CREATE TABLE IF NOT EXISTS import_row_results (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    import_run_id          TEXT NOT NULL REFERENCES import_runs(import_run_id),
    source_file_hash       TEXT NOT NULL,
    row_index              INTEGER NOT NULL,
    template_id            TEXT,
    status                 TEXT NOT NULL,
    reason                 TEXT,
    warnings_json          TEXT,
    requested_supersedes_id TEXT,
    persisted_supersedes_id TEXT,
    diff_json              TEXT,
    backfill_raw           TEXT,
    retry_count            INTEGER NOT NULL DEFAULT 0,
    created_at             TEXT NOT NULL,
    UNIQUE(import_run_id, row_index)
);

CREATE INDEX IF NOT EXISTS ix_import_runs_status ON import_runs(status);
CREATE INDEX IF NOT EXISTS ix_import_row_results_hash_row ON import_row_results(source_file_hash, row_index);
CREATE INDEX IF NOT EXISTS ix_import_row_results_template ON import_row_results(template_id);
```

#### DAO additions in `db.py`

Add import-specific DAO helpers mirroring the existing run helpers:

- `create_import_run(...)`
- `acquire_import_lock(...)`
- `release_import_lock(import_run_id: str)`
- `finalize_import_run(...)`
- `get_import_run(import_run_id: str)`
- `get_terminal_row_results_by_hash(source_file_hash: str)`
- `get_template_by_id(template_id: str)`
- `update_template_in_place(...)`
- `record_import_row_result(...)`
- `count_prompt_rows_for_template_hash(style_text_hash: str)`

`update_template_in_place(...)` must recompute `style_text_hash` exactly as `insert_template(...)` does.

### 5.5 Config contract

Add these validated config fields in `config.py`:

- `comicbook_import_max_rows_per_file: int = 1000`
- `comicbook_import_max_file_bytes: int = 5_000_000`
- `comicbook_import_allow_external_path: bool = False`
- `comicbook_import_backfill_model: str = "gpt-5.4-mini"`

Reuse existing:

- `comicbook_runs_dir`
- `comicbook_logs_dir`
- Azure endpoint, API key, API version, and chat deployment

Do **not** add an import-specific output-dir setting in v1.

---

## 6. Node-level design

### 6.1 `upload_load_file`

Responsibilities:

- resolve the source path when reading from disk
- enforce path policy and file-size cap
- read bytes once
- compute `sha256`
- decode UTF-8
- parse either bare-array or envelope form

Hard failures from this node:

- missing/unreadable path
- resolved path outside the allowed tree when external paths are disallowed
- file larger than `comicbook_import_max_file_bytes`
- malformed JSON
- top-level shape other than allowed array or versioned envelope

Implementation notes:

- if reading from stdin, set `source_label = "<stdin>"` and `source_file_path = None`
- include JSON line/column and a short offending snippet in parse errors

### 6.2 `upload_parse_and_validate`

Responsibilities:

- normalize each row to `TemplateImportRow`
- reject non-object items
- validate required fields and field types
- capture unknown fields as warnings, not failures
- override incoming `created_by_run` by ignoring it and warning
- set backfill flags and requested supersedes value
- enforce `comicbook_import_max_rows_per_file`

Row-level validation failures stay on the row and do not abort the run.

### 6.3 `upload_resume_filter`

Responsibilities:

- load prior terminal row results for the same `source_file_hash`
- mark rows with prior statuses in `{inserted, updated, skipped_duplicate}` as `skipped_resume`
- copy computed `retry_count` for rows that will be retried

This node must not write to the database.

### 6.4 `upload_backfill_metadata`

Responsibilities:

- call `router_llm` through a thin structured helper dedicated to metadata generation
- fill only the fields still missing after validation and flag resolution
- track token usage and estimated cost in `UsageTotals`
- honor `--no-backfill`, `--allow-missing-optional`, and `--budget-usd`
- implement a circuit breaker after two consecutive retry-exhausted transport failures

Failure behavior:

- backfill-disabled rows become `failed:backfill_disabled` unless `--allow-missing-optional` is active
- schema-invalid or retry-exhausted transport failures become row-level failures
- when the circuit breaker trips, remaining rows that still need backfill fail with `metadata_backfill_short_circuit`

### 6.5 `upload_decide_write_mode`

Responsibilities:

- skip rows with validation errors or prior terminal failure decisions
- look up existing template rows by id
- choose `insert`, `update`, `skip`, or `defer`
- attach enough existing-row data for diff generation later

`defer` is internal-only and is used for unresolved same-run `supersedes_id` targets.

### 6.6 `upload_persist`

Responsibilities:

- perform insert or update decisions serially
- compute full diff maps for updates
- turn zero-diff updates into `skipped_duplicate`
- log all diffs as structured events
- write the matching `import_row_results` record in the same transaction

Atomicity rule:

- one row transaction at a time
- no row result is committed without its matching template write decision being committed

For update diffs:

- include changed fields among `name`, `style_text`, `style_text_hash`, `tags`, `summary`, `created_at`, `created_by_run`, `supersedes_id`
- log full hashes for `style_text_hash`
- include a preview for `style_text` unless redaction is enabled

### 6.7 `upload_summarize`

Responsibilities:

- compute final counts and run status
- finalize `import_runs`
- write `runs/<import_run_id>/import_report.md`
- write `logs/<import_run_id>.import.jsonl`
- surface prior retry counts and fingerprint-drift counts for updated rows

Run-status rules:

- `succeeded`: no row failures
- `partial`: at least one row failed but the run completed normally
- `failed`: hard workflow failure after import-run creation
- `dry_run`: all rows completed without DB template writes and no hard failure

---

## 7. Observability, failure handling, and acceptance rules

### 7.1 Structured logging

Use JSON lines with these common fields:

- `import_run_id`
- `node`
- `event`
- `row_index` when applicable
- `template_id` when known
- `status`
- `retry_count` when applicable

Important event types:

- `import_started`
- `row_skipped_resume`
- `metadata_backfill_requested`
- `metadata_backfill_failed`
- `template_inserted`
- `template_updated`
- `template_skipped_duplicate`
- `supersedes_unresolved`
- `import_finished`

### 7.2 Report contents

`import_report.md` must include:

- source label, hash, import run id, timestamps, final status
- counts for inserted, updated, skipped duplicate, skipped resume, failed, backfilled, warnings
- total estimated backfill cost
- per-row terminal table with row index, template id, status, reason/warnings, retry count
- detailed diff sections for updated rows
- explicit warning section for unresolved `supersedes_id` values that were persisted as `NULL`
- fingerprint-drift summary for updated rows whose `style_text_hash` changed

### 7.3 Failure handling rules

- malformed input file: hard fail before any row processing
- row validation issue: row failure only
- backfill failure: row failure only
- DB integrity issue on one row: row failure only
- import lock conflict: hard fail before graph execution
- unhandled exception after import run starts: finalize `import_runs` as `failed`

### 7.4 Acceptance rules to preserve during implementation

The implementation is not done until all of these are true:

- unchanged sample input imports successfully
- rerunning the unchanged sample skips prior terminal-success rows by resume
- updating an existing template produces exactly one diff-bearing update result
- missing metadata triggers exactly one backfill call per affected row unless disabled
- `created_by_run` is always stored as `workflow_import`
- `tags: []` stays an empty list and does not trigger backfill
- unresolved `supersedes_id` values never violate the DB foreign key; they are surfaced as warnings and stored as `NULL`
- the image workflow still runs unchanged against a database after template-import activity

---

## 8. Ordered implementation plan

The implementation team should execute these `TaskGroup`s sequentially.

## TaskGroup TG1 — Lock the contract with focused failing tests

**Goal**  
Establish the new workflow's contract before changing runtime behavior.

**Dependencies**  
None.

**Detailed tasks**

1. Add focused pytest files for the planned upload helpers and CLI contract.
2. Extend `test_db.py` with failing expectations for new import tables, DAO methods, and import lock behavior.
3. Add failing tests for:
   - bare-array and envelope input parsing
   - `tags: []` staying non-backfilled
   - zero-diff update returning `skipped_duplicate`
   - unresolved `supersedes_id` becoming warning + `NULL`
   - resume skipping only prior terminal successes
4. Add a failing CLI test for positional file path vs `--stdin` validation.

**Expected files or modules**

- `ComicBook/tests/test_upload_load_file.py`
- `ComicBook/tests/test_upload_parse_and_validate.py`
- `ComicBook/tests/test_upload_resume_filter.py`
- `ComicBook/tests/test_upload_persist.py`
- `ComicBook/tests/test_upload_run_cli.py`
- `ComicBook/tests/test_db.py`

**Exit criteria**

- New tests exist and fail for missing upload implementation rather than for broken fixtures.
- The desired runtime contract is locked in pytest assertions.

**Handoff notes for next group**

- Do not start node implementation until the persistence and config contract is represented in tests.

## TaskGroup TG2 — Add shared persistence, config, and state scaffolding

**Goal**  
Extend shared modules so the upload workflow has stable contracts for state, config, and SQL.

**Dependencies**  
TG1 complete.

**Detailed tasks**

1. Extend `state.py` with import-specific statuses and TypedDicts.
2. Extend `config.py` with import guardrail settings and validation.
3. Extend `db.py` schema with `import_runs` and `import_row_results`.
4. Add import-run lock helpers mirroring the existing `runs` lock policy.
5. Add `get_template_by_id`, `update_template_in_place`, and prompt-drift counting helpers.
6. Add or extend DB/config tests until TG2 passes.

**Expected files or modules**

- `ComicBook/comicbook/state.py`
- `ComicBook/comicbook/config.py`
- `ComicBook/comicbook/db.py`
- `ComicBook/tests/test_db.py`
- `ComicBook/tests/test_config.py`

**Exit criteria**

- Schema initializes idempotently with new import tables and indexes.
- Import lock behavior is covered by tests.
- Shared contracts compile cleanly and existing image-workflow tests still pass in focused scope.

**Handoff notes for next group**

- From this point onward, node work must use the new shared contracts rather than inventing local copies.

## TaskGroup TG3 — Implement file ingest, validation, and resumability

**Goal**  
Create the front half of the workflow: file loading, normalization, and skip-on-rerun behavior.

**Dependencies**  
TG2 complete.

**Detailed tasks**

1. Implement `upload_load_file.py` for path resolution, size checks, JSON parsing, envelope normalization, and hashing.
2. Implement `upload_parse_and_validate.py` for row normalization, warnings, and validation errors.
3. Implement `upload_resume_filter.py` using the new row-result DAO helper.
4. Ensure retry counts are attached to retried rows.
5. Add direct node-level tests without importing the graph.

**Expected files or modules**

- `ComicBook/comicbook/nodes/upload_load_file.py`
- `ComicBook/comicbook/nodes/upload_parse_and_validate.py`
- `ComicBook/comicbook/nodes/upload_resume_filter.py`
- matching new tests

**Exit criteria**

- Valid sample input loads into normalized row state.
- malformed input hard-fails before any DB write.
- resume-filter logic skips only prior terminal successes.

**Handoff notes for next group**

- The next group may assume `parsed_rows` and `rows_to_process` are trustworthy and typed.

## TaskGroup TG4 — Implement backfill, write-mode routing, and persistence

**Goal**  
Finish row-level behavior from optional metadata generation through durable DB writes.

**Dependencies**  
TG3 complete.

**Detailed tasks**

1. Add `metadata_prompts.py` with prompt text and strict JSON schema.
2. Implement `upload_backfill_metadata.py` using `router_llm` transport helpers, token accounting, budget checks, and circuit-breaker logic.
3. Implement `upload_decide_write_mode.py` with `insert`/`update`/`skip`/`defer` selection.
4. Implement `upload_persist.py` with:
   - insert behavior
   - update-in-place behavior
   - diff generation
   - zero-diff `skipped_duplicate`
   - unresolved `supersedes_id` null fallback
   - single-row transaction commit
5. Add direct unit tests for each new node and DAO interaction path.

**Expected files or modules**

- `ComicBook/comicbook/metadata_prompts.py`
- `ComicBook/comicbook/nodes/upload_backfill_metadata.py`
- `ComicBook/comicbook/nodes/upload_decide_write_mode.py`
- `ComicBook/comicbook/nodes/upload_persist.py`
- matching tests

**Exit criteria**

- Insert, update, duplicate-skip, backfill, and row-failure paths are all green in focused pytest scope.
- No test shows partial template writes without matching row-result writes.

**Handoff notes for next group**

- The graph/CLI layer should treat row nodes as stable and should not duplicate persistence rules.

## TaskGroup TG5 — Wire the graph, CLI, package export, and reporting

**Goal**  
Expose the workflow as a usable runtime and library surface with final reporting.

**Dependencies**  
TG4 complete.

**Detailed tasks**

1. Implement `upload_graph.py` with ordered node wiring and conditional routing.
2. Implement `upload_run.py`:
   - argument parsing
   - managed dependency lifecycle
   - import-lock handling
   - exit-code mapping
   - final stdout summary
3. Re-export `upload_templates` from `comicbook.__init__`.
4. Implement `upload_summarize.py` with report generation and import-run finalization.
5. Add integration tests for happy path, partial success, resume, dry-run, and lock contention.

**Expected files or modules**

- `ComicBook/comicbook/upload_graph.py`
- `ComicBook/comicbook/upload_run.py`
- `ComicBook/comicbook/__init__.py`
- `ComicBook/comicbook/nodes/upload_summarize.py`
- `ComicBook/tests/test_upload_graph.py`
- `ComicBook/tests/test_upload_run_cli.py`

**Exit criteria**

- `python -m comicbook.upload_run docs/planning/template-upload-workflow/sample_input.json` works in mocked/local test conditions.
- The library helper and CLI use the same execution path.
- Reports and structured logs are emitted to the existing `runs/` and `logs/` roots.

**Handoff notes for next group**

- Final verification must now broaden beyond focused unit tests and update the documentation triad.

## TaskGroup TG6 — Verification, documentation triad, and closeout

**Goal**  
Prove the workflow is shippable and bring all durable docs into sync.

**Dependencies**  
TG5 complete.

**Detailed tasks**

1. Run focused then broader pytest scopes.
2. Run one opt-in live Azure smoke test when credentials are available.
3. Add workflow docs under:
   - `docs/business/template-upload-workflow/index.md`
   - `docs/developer/template-upload-workflow/index.md`
4. Update `docs/index.md`, `docs/business/index.md`, `docs/developer/index.md`, and any workflow indexes affected by the new docs.
5. Decide whether an ADR is required based on the final implementation shape. If implementation materially changes the approved persistence or concurrency design, add an ADR under `docs/planning/adr/`.
6. Verify sample commands and examples match shipped behavior.

**Expected files or modules**

- documentation files listed above
- any needed index updates
- optional ADR if final code changes the durable architecture

**Exit criteria**

- Required acceptance criteria are green.
- Business and developer docs exist and are indexed.
- Any ADR-worthy deviations are recorded.

**Handoff notes for next group**

- No further implementation slice should begin until the docs gate is satisfied.

---

## 9. Minimum pytest scopes for implementation

Recommended progression:

1. `pytest -q tests/test_db.py tests/test_config.py`
2. `pytest -q tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py`
3. `pytest -q tests/test_upload_backfill_metadata.py tests/test_upload_decide_write_mode.py tests/test_upload_persist.py`
4. `pytest -q tests/test_upload_graph.py tests/test_upload_run_cli.py`
5. `pytest -q`

Run focused scopes first and broaden only after the narrower layer is green.

---

## 10. Final delivery checklist

- [ ] TG1-TG6 complete in order
- [ ] upload workflow implemented without touching `DoNotChange/`
- [ ] shared-module changes are minimal and covered by tests
- [ ] resume behavior proven against repeated runs of the same file hash
- [ ] zero-diff updates reported as `skipped_duplicate`
- [ ] unresolved `supersedes_id` values never break the SQLite FK
- [ ] backfill usage and cost are visible in logs and reports
- [ ] image workflow still works unchanged
- [ ] business and developer docs added and indexed before declaring the change done

---

*End of implementation guide.*
