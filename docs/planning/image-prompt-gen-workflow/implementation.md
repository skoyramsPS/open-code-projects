# Technical Implementation Guide: Input File Support for the Image Prompt Generation Workflow

**Status:** Draft for implementation  
**Date:** 2026-04-23  
**Source planning document:** `docs/planning/image-prompt-gen-workflow/input-file-support-design.md`  
**Audience:** delivery team  
**Authority:** This document is the primary build document for the JSON/CSV input-file-support change. It is written to be executable without reopening the source planning document during implementation.

---

## 1. Purpose and scope

This guide defines how to add JSON and CSV prompt-file support to the already shipped `ComicBook` workflow runtime.

The current repository already has a working single-prompt workflow with these stable characteristics:

- the graph and `RunState` are single-prompt
- `comicbook.run.run_once(...)` executes one prompt at a time
- each run has one `run_id`
- per-run artifacts are written to `runs/<run_id>/report.md`, `logs/<run_id>.summary.json`, and `image_output/<run_id>/`
- persistence uses the existing SQLite schema and one-active-run-per-database lock policy

This change adds a **CLI/runtime entry-layer batch wrapper** that reads a file, validates it completely, and then invokes the existing single-prompt workflow once per record in serial order.

This change does **not** redesign the graph, add batch tables, add parallel execution, or change cache/persistence semantics.

---

## 2. Current baseline in the repository

Implementation must align with the current codebase, not with a hypothetical clean-slate design.

Relevant current modules and surfaces:

- `ComicBook/comicbook/run.py`
  - `parse_args(...)` currently accepts one positional `user_prompt`
  - `run_once(...)` is the single-prompt library entry point
  - `main(...)` prints a small JSON payload with `run_id` and `run_status`
- `ComicBook/comicbook/graph.py`
  - assembles the existing single-prompt LangGraph workflow
- `ComicBook/comicbook/execution.py`
  - prepares input state, acquires the run lock, and finalizes crash cases
- `ComicBook/comicbook/state.py`
  - keeps the graph contract single-prompt today
- `ComicBook/tests/`
  - already contains runtime, CLI, and graph tests
- `ComicBook/README.md`
  - documents the current single-prompt CLI

The implementation must preserve those existing contracts unless this guide explicitly changes them.

---

## 3. Resolved ambiguities and locked decisions

The planning addendum contains a few places where the intended runtime surface could be interpreted more than one way. These decisions are locked for implementation.

### 3.1 Prompt-source contract

**Decision:** keep the existing positional prompt argument and add `--input-file`; do **not** introduce `--user-prompt` in this change.

Why:

- the shipped CLI already uses a positional prompt
- the acceptance criteria later in the planning addendum refer to positional prompt or `--input-file`
- keeping the positional argument is the smallest backward-compatible change

Final CLI contract:

- `python -m comicbook.run "<prompt>"`
- `python -m comicbook.run --input-file <path>`

Exactly one prompt source must be provided.

### 3.2 Graph boundary

**Decision:** keep the graph, nodes, and `RunState` single-prompt.

Implementation must not:

- add batch fields to `RunState`
- add graph nodes for file parsing
- add batch-aware persistence to `comicbook.db`
- make `run_once(...)` sometimes return a list and sometimes a single state

### 3.3 Batch helper location

**Decision:** keep `run_once(...)` unchanged and add a separate `run_batch(...)` helper in `ComicBook/comicbook/run.py`.

Why:

- it preserves the stable single-prompt library API
- it lets the CLI and tests share one batch execution path
- it avoids reopening config, HTTP clients, and DB connections once per record when a batch is run in one process

### 3.4 Validation timing

**Decision:** parse and validate the entire input file before the first workflow run starts.

That validation must catch, before execution:

- unsupported file extension
- unreadable file / malformed JSON / malformed CSV
- invalid top-level JSON shape
- missing required fields or columns
- blank `user_prompt`
- blank `run_id`
- duplicate `run_id` values within the file
- unsupported JSON fields or CSV columns

### 3.5 Run ID handling in file mode

**Decision:** pre-resolve a `run_id` for every record before invoking the workflow.

Rules:

- if the record supplies `run_id`, use it
- otherwise generate it in the batch wrapper before calling `run_once(...)`
- CLI `--run-id` is rejected whenever `--input-file` is used

Why this is required:

- batch summary reporting needs a stable `run_id` even if one record later crashes
- `run_once(...)` currently lets the graph assign a run ID; that is fine for single runs but too late for reliable batch bookkeeping

### 3.6 Exit semantics

**Decision:** file mode continues through all validated records even if one record fails at runtime, then returns a final batch summary.

Exit status rules:

- prompt-source contract errors use `argparse` validation and exit with CLI usage failure semantics
- input-file parse/validation failures exit non-zero before any run starts
- batch execution exits non-zero if any record ends `failed` or `partial`
- `dry_run` counts as a non-failing outcome for batch summary purposes

### 3.7 Scope boundaries

This change does **not** include:

- stdin support
- per-record overrides for `panels`, `force`, `budget_usd`, `dry_run`, or `redact_prompts`
- batch-level SQLite tables or batch-level report files
- concurrent execution
- changes to fingerprinting, router behavior, image generation, or artifact paths

---

## 4. Repository impact and module boundaries

Implementation should stay concentrated at the CLI/runtime boundary.

### 4.1 Files expected to change

```text
ComicBook/
  comicbook/
    run.py                     # update: CLI contract, batch helper, batch summary
    input_file.py              # new: JSON/CSV parsing + validation models/helpers
  examples/
    prompts.sample.json        # new: reference input file
    prompts.sample.csv         # new: reference input file
  tests/
    test_input_file_support.py # new: focused contract, parser, and batch tests
  README.md                    # update when implementation lands
docs/
  planning/
    image-prompt-gen-workflow/
      implementation.md        # this guide
      index.md                 # update description if needed
  business/
    image-prompt-gen-workflow/index.md   # update when runtime surface changes
  developer/
    image-prompt-gen-workflow/index.md   # update when runtime surface changes
```

### 4.2 Files expected to remain unchanged

Unless testing reveals a genuine integration gap, do **not** change:

- `ComicBook/comicbook/graph.py`
- `ComicBook/comicbook/execution.py`
- `ComicBook/comicbook/db.py`
- `ComicBook/comicbook/fingerprint.py`
- `ComicBook/comicbook/router_*`
- `ComicBook/comicbook/image_client.py`
- `ComicBook/comicbook/nodes/*`

The design is specifically intended to avoid touching the workflow graph internals.

### 4.3 Module responsibilities

#### `comicbook/input_file.py` (new)

Owns all file-format concerns:

- input-record model(s)
- JSON loading
- CSV loading
- normalization and trimming
- duplicate detection
- unsupported-field / unsupported-column rejection
- path/extension validation
- error messages suitable for CLI display and pytest assertions

This module must be pure parsing/validation code. It must not execute workflow runs, open HTTP clients, or talk to the database.

#### `comicbook/run.py` (updated)

Owns runtime entry concerns:

- CLI argument parsing for prompt source selection
- batch orchestration over validated records
- reuse of one managed config/DB/http-client set per CLI invocation
- per-record invocation of `run_once(...)`
- batch summary JSON emission
- final process exit code

`run.py` must remain the only place that knows how to bridge CLI input-file mode into repeated single-run workflow calls.

---

## 5. Runtime contracts

### 5.1 CLI contract

The final CLI surface for this change is:

```bash
uv run python -m comicbook.run "A four-panel comic of a wandering sage at sunrise"
uv run python -m comicbook.run --input-file ComicBook/examples/prompts.sample.json
uv run python -m comicbook.run --input-file ComicBook/examples/prompts.sample.csv --dry-run
```

Argument rules:

- positional `user_prompt` becomes optional in argparse (`nargs="?"`)
- add `--input-file <path>`
- require exactly one of positional `user_prompt` or `--input-file`
- keep existing `--dry-run`, `--force`, `--panels`, `--budget-usd`, and `--redact-prompts`
- reject `--run-id` when `--input-file` is present

Implementation note:

- `argparse` mutual-exclusion groups do not cleanly support the current positional prompt shape, so enforce the exclusivity rules with post-parse validation in `parse_args(...)`

### 5.2 Input-record contract

Add a strict record model in `comicbook/input_file.py`.

Recommended shape:

```python
class InputPromptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_prompt: str
    run_id: str | None = None

    @field_validator("user_prompt")
    @classmethod
    def validate_user_prompt(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("user_prompt must not be blank")
        return normalized

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("run_id must not be blank when provided")
        return normalized
```

Required behaviors:

- reject unknown JSON keys
- reject unsupported CSV columns
- trim whitespace from JSON strings and CSV cell values
- preserve file order after validation
- reject duplicate non-null `run_id` values within the file before execution begins

### 5.3 Supported file formats

### JSON

- file must decode as UTF-8 text
- top-level value must be a list
- each item must be an object validated as `InputPromptRecord`

Supported shape:

```json
[
  {
    "user_prompt": "A cinematic portrait of a forest guardian in moonlight"
  },
  {
    "run_id": "sample-batch-002",
    "user_prompt": "A three-panel comic of a clockmaker fixing time itself"
  }
]
```

### CSV

- file must decode as UTF-8 text; use `utf-8-sig` when opening so BOM-prefixed CSVs still parse cleanly
- header row is required
- supported columns are exactly `user_prompt` and optional `run_id`
- any extra column fails validation

Supported shape:

```csv
run_id,user_prompt
sample-batch-001,"A cinematic portrait of a forest guardian in moonlight"
sample-batch-002,"A three-panel comic of a clockmaker fixing time itself"
```

### 5.4 Batch execution contract

Add a separate helper:

```python
def run_batch(
    records: Sequence[InputPromptRecord],
    *,
    input_file: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    panels: int | None = None,
    budget_usd: float | None = None,
    redact_prompts: bool = False,
    deps: Deps | None = None,
    dotenv_path: str | Path = ".env",
) -> dict[str, object]:
    ...
```

Contract rules:

- `run_once(...)` remains the authoritative single-prompt executor
- `run_batch(...)` loops over records in validated file order
- all global CLI flags apply identically to every record
- each record executes as its own normal workflow run with its own `run_id`
- when `deps is None`, create managed runtime deps once and reuse them for the whole batch
- if a record does not provide `run_id`, generate one before calling `run_once(...)`
- catch per-record exceptions, record them as failed outcomes, and continue to the next validated record

The summary returned by `run_batch(...)` and printed by `main(...)` in file mode must include at least:

- `input_file`
- `total_records`
- `succeeded`
- `partial`
- `dry_run`
- `failed`
- `run_ids`

No batch-level SQLite rows or report files are created in v1.

### 5.5 Persistence contract

Persistence behavior is unchanged:

- one input-file record == one normal workflow run
- each record acquires/releases the existing per-run SQLite lock through the current runtime path
- each record writes the existing `runs`, `logs`, and `image_output` artifacts
- resume remains per run, not per batch
- rerunning a file resumes prior work only for records whose `run_id` values are stable and repeated

### 5.6 Observability contract

The implementation must make file-mode behavior observable without inventing new durable storage.

Required visibility:

- validation failures identify file path and record/row context when possible
- per-record execution order is deterministic and follows file order
- final stdout contains the batch summary JSON
- existing per-run logs/reports remain the source of detailed run diagnostics

Recommended non-persisted log lines from `run.py`:

- `starting batch record 2/5 run_id=...`
- `completed batch record 2/5 run_id=... status=...`
- `batch record 2/5 run_id=... failed: ...`

---

## 6. Failure handling rules

Implementation must treat failure classes differently.

### 6.1 CLI contract failures

Examples:

- neither prompt source provided
- both prompt sources provided
- `--run-id` combined with `--input-file`

Handling:

- reject in `parse_args(...)`
- present as CLI usage errors
- start no workflow runs

### 6.2 Input-file validation failures

Examples:

- unreadable file
- malformed JSON/CSV
- unsupported fields/columns
- blank prompt
- duplicate `run_id`

Handling:

- fail before the first workflow run
- return non-zero exit code
- do not create any per-run artifacts

### 6.3 Per-record runtime failures

Examples:

- router failure after repair exhaustion
- lock acquisition failure for a record
- budget-blocked run
- image-generation partial failure
- unexpected exception escaping `run_once(...)`

Handling:

- keep already validated later records eligible to run
- classify the record result using the final run status when available
- if an exception escapes before a final state is returned, count that record as `failed` using the pre-resolved `run_id`
- overall batch exit is non-zero if any record is `failed` or `partial`

---

## 7. Testing requirements

When the delivery team implements this guide, the Python testing gate applies. The code change is user-visible runtime behavior in Python, so implementation must follow `pytest-tdd-guard`.

### 7.1 Required test coverage

Add focused tests for:

1. CLI prompt-source validation
   - positional prompt only succeeds
   - `--input-file` only succeeds
   - both prompt sources fail
   - neither prompt source fails
   - `--run-id` with `--input-file` fails

2. JSON parsing and validation
   - valid list of records parses in order
   - non-list top level fails
   - blank `user_prompt` fails
   - duplicate `run_id` fails
   - unknown field fails

3. CSV parsing and validation
   - valid CSV parses in order
   - missing `user_prompt` column fails
   - blank prompt cell fails
   - duplicate `run_id` fails
   - unsupported extra column fails

4. Batch runtime behavior
   - records execute serially in file order
   - all global flags are passed to every `run_once(...)` invocation
   - omitted `run_id` values are generated before execution
   - a failing record does not stop later validated records
   - summary counts are correct
   - exit code is non-zero when any record is `partial` or `failed`

5. Single-run regression safety
   - existing positional single-prompt CLI still works unchanged
   - existing `run_once(...)` behavior and return shape stay single-prompt

### 7.2 Suggested pytest layout

Prefer one new focused test module:

- `ComicBook/tests/test_input_file_support.py`

Only touch existing test modules if necessary for shared fixtures.

### 7.3 Suggested pytest command progression

From `ComicBook/`:

```bash
uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q tests/test_input_file_support.py
uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q tests/test_input_file_support.py tests/test_budget_guard.py
uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q
```

---

## 8. Ordered implementation plan

Implement the change as the following sequential `TaskGroup`s.

### TaskGroup TG1 - Lock the contract with tests first

**Goal**  
Create failing tests that define the new CLI and file-validation behavior before production code changes begin.

**Dependencies**  
None.

**Detailed tasks**

1. Add `ComicBook/tests/test_input_file_support.py`.
2. Write tests for CLI argument exclusivity and `--run-id` rejection in file mode.
3. Write tests for JSON and CSV happy paths plus the required validation failures.
4. Write tests for batch serial ordering and summary counting using fake execution behavior or monkeypatched `run_once(...)`.
5. Keep tests narrow and deterministic; do not involve the real graph or real Azure traffic for parser/CLI contract tests.

**Expected files or modules**

- `ComicBook/tests/test_input_file_support.py`

**Exit criteria**

- the new tests exist and fail for the expected reasons against the current runtime
- the failing tests capture all locked decisions in Sections 3-7 of this guide

**Handoff notes for TG2**

- TG2 should implement only enough parsing/validation code to turn the TG1 parser tests green
- do not mix CLI orchestration changes into the parser module work yet

### TaskGroup TG2 - Implement input-file parsing and validation

**Goal**  
Add a standalone parsing module that fully validates JSON and CSV files into ordered in-memory records before any workflow execution begins.

**Dependencies**  
TG1 complete.

**Detailed tasks**

1. Create `ComicBook/comicbook/input_file.py`.
2. Add `InputPromptRecord` and a dedicated validation/error type.
3. Implement file-type dispatch by path suffix for `.json` and `.csv` only.
4. Implement JSON loader with top-level-list enforcement and per-item validation.
5. Implement CSV loader with header enforcement, trimming, exact-column validation, and per-row validation.
6. Add duplicate `run_id` detection across the full validated record list.
7. Keep all parsing functions free of DB, HTTP, or graph dependencies.
8. Make validation errors include enough context for debugging, such as file path and row/item index when available.

**Expected files or modules**

- `ComicBook/comicbook/input_file.py`
- `ComicBook/tests/test_input_file_support.py`

**Exit criteria**

- all parser-specific TG1 tests pass
- loading a valid JSON or CSV file returns ordered validated records
- no workflow run can start after a file validation failure

**Handoff notes for TG3**

- TG3 should treat TG2's parser output as authoritative input
- do not duplicate file validation logic inside `run.py`

### TaskGroup TG3 - Add batch runtime orchestration to the CLI boundary

**Goal**  
Teach the runtime to accept either a direct prompt or an input file while preserving the single-prompt workflow internals.

**Dependencies**  
TG2 complete.

**Detailed tasks**

1. Update `parse_args(...)` in `ComicBook/comicbook/run.py`:
   - make positional `user_prompt` optional
   - add `--input-file`
   - enforce exactly one prompt source
   - reject `--run-id` with `--input-file`
2. Add `run_batch(...)` in `ComicBook/comicbook/run.py`.
3. Reuse one managed `Deps`/DB/http-client set for the full batch when the caller did not inject deps.
4. Pre-resolve a `run_id` for every record before calling `run_once(...)`.
5. Execute records serially in validated file order.
6. Pass `dry_run`, `force`, `panels`, `budget_usd`, and `redact_prompts` to every record run unchanged.
7. Catch per-record exceptions, mark those records failed in the batch summary, and continue.
8. Update `main(...)` so:
   - single-prompt mode keeps the existing `{run_id, run_status}` output
   - file mode prints the batch summary JSON
   - file mode returns non-zero when any record is `partial` or `failed`

**Expected files or modules**

- `ComicBook/comicbook/run.py`
- `ComicBook/comicbook/input_file.py`
- `ComicBook/tests/test_input_file_support.py`

**Exit criteria**

- single-prompt CLI behavior remains backward compatible
- file mode executes one normal workflow run per record in order
- file mode never mutates the graph or DB schema
- batch summary counts and exit codes match the contract in this guide

**Handoff notes for TG4**

- TG4 must treat TG3's runtime surface as the source of truth for docs and sample files
- if TG3 required any unplanned runtime-contract deviation, document and resolve it before writing user-facing docs

### TaskGroup TG4 - Add reference files, docs, and acceptance closeout

**Goal**  
Ship the operator and maintainer documentation and example files that make the new runtime surface usable.

**Dependencies**  
TG3 complete.

**Detailed tasks**

1. Add `ComicBook/examples/prompts.sample.json` with at least two safe prompts and one explicit `run_id` example.
2. Add `ComicBook/examples/prompts.sample.csv` with the same supported shape.
3. Update `ComicBook/README.md` with file-mode examples and the `--run-id` restriction in file mode.
4. Update `docs/business/image-prompt-gen-workflow/index.md` in plain language:
   - what input files are supported
   - what operators can expect
   - the no-per-row-overrides limitation
   - resume expectations when `run_id` is or is not supplied
5. Update `docs/developer/image-prompt-gen-workflow/index.md` with module boundaries, parser/runtime responsibilities, and test coverage.
6. Update `docs/planning/image-prompt-gen-workflow/index.md` if document descriptions need to reflect the new implementation guide scope or any added docs.
7. Run the focused and full pytest scopes and record results in the implementation handoff if that handoff is still used for execution tracking.

**Expected files or modules**

- `ComicBook/examples/prompts.sample.json`
- `ComicBook/examples/prompts.sample.csv`
- `ComicBook/README.md`
- `docs/business/image-prompt-gen-workflow/index.md`
- `docs/developer/image-prompt-gen-workflow/index.md`
- `docs/planning/image-prompt-gen-workflow/index.md`

**Exit criteria**

- sample files match the actual parser contract
- operator-facing docs match the actual CLI syntax
- developer docs explain where parsing ends and workflow execution begins
- full pytest scope passes

**Handoff notes for subsequent work**

- no ADR is required if the delivered change stays a CLI-level serial wrapper with no new persistence or graph architecture
- create or update an ADR only if scope expands into batch persistence, per-record overrides, or graph-level multi-prompt state

---

## 9. Acceptance criteria for this change

The implementation is complete when all items below are true.

1. The CLI accepts exactly one prompt source: positional prompt or `--input-file`.
2. `run_once(...)` remains a single-prompt API and return shape.
3. A new parser module validates JSON and CSV files fully before any workflow execution begins.
4. JSON supports a top-level list of `{user_prompt, optional run_id}` objects only.
5. CSV supports `user_prompt` and optional `run_id` columns only.
6. Blank prompts, blank run IDs, duplicates, malformed files, and unsupported fields/columns fail validation before execution.
7. `--run-id` is rejected in file mode.
8. File records execute serially in file order.
9. Every file record produces one normal workflow run with the existing per-run artifacts.
10. Global flags `--dry-run`, `--force`, `--panels`, `--budget-usd`, and `--redact-prompts` apply uniformly to every record.
11. File mode prints a batch summary JSON containing at least `input_file`, `total_records`, `succeeded`, `partial`, `dry_run`, `failed`, and `run_ids`.
12. File mode exits non-zero when any record is `partial` or `failed`, or when the file fails validation.
13. Sample JSON and CSV files exist under `ComicBook/examples/` and reflect the real parser contract.
14. Updated business and developer docs explain the new user-visible behavior and maintainer boundaries.

---

## 10. ADR and documentation-gate assessment

### ADR

No ADR is required for the planned implementation in this guide because the change remains:

- a CLI/runtime input-format extension
- a serial wrapper around the existing single-prompt workflow
- compatible with the current per-run persistence, reporting, and resume model

Create an ADR only if scope expands beyond those limits.

### Documentation gate

When the code change described by this guide is implemented, the full documentation triad update is required because the runtime surface becomes user-visible and maintainer-visible.

For this planning-document task itself, the full triad is **not** required yet because this repo change only creates the planning implementation guide and does not itself ship the runtime behavior.

---

## 11. Remaining assumptions and unresolved decisions

These items are assumed for implementation unless new evidence requires a follow-up planning update.

1. The batch wrapper can reuse one managed `Deps` container safely across sequential record runs in a single process.
2. Existing lock acquisition/finalization behavior remains sufficient when invoked multiple times serially in one process.
3. The current CLI should keep its single-run JSON output unchanged and only emit the new batch summary shape in file mode.
4. File-content validation errors can be represented by a new parser-specific exception without changing graph-level error models.

There are no open architectural blockers in the planning material for the narrow v1 input-file-support scope.
