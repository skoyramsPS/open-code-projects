# Design Addendum: JSON and CSV Input File Support

**Status:** Proposed
**Date:** 2026-04-23
**Workflow:** Image Prompt Generation Workflow
**Related docs:** `plan.md`, `implementation.md`, `ComicBook/comicbook/run.py`

---

## 1. Summary

This addendum proposes a CLI enhancement that allows the workflow to accept prompt input from either:

- a single positional prompt string, or
- an `--input-file` pointing to a JSON or CSV file

The design intentionally keeps the workflow graph and `RunState` contract single-prompt. File input support is added at the CLI/runtime entry layer as a serial batch wrapper that invokes the existing workflow once per input record.

That choice preserves the current graph shape, cache behavior, resume behavior, SQLite locking policy, report layout, and test surface while still giving operators a practical way to submit multiple prompts from a file.

---

## 2. Problem Statement

Today the workflow entry point accepts a single positional `user_prompt`.

Current CLI shape in `ComicBook/comicbook/run.py`:

```python
parser.add_argument("user_prompt")
```

That is sufficient for one-off runs but awkward for:

- running a curated list of prompts from a file
- preparing repeatable operator input sets
- sharing examples that can be executed without retyping prompt text
- testing cache behavior or repeated workflow execution across a known batch

The requested enhancement is support for:

- `--input-file prompts.json`
- `--input-file prompts.csv`

with the rule that exactly one prompt source must be provided: either a direct string prompt or an input file.

---

## 3. Goals and Non-Goals

### 3.1 Goals

1. Allow operators to run the existing workflow from a JSON or CSV file.
2. Require exactly one input source:  `user_prompt` or `--input-file`.
3. Preserve the existing single-run, single-prompt workflow internals.
4. Keep execution serial and compatible with the current one-active-run-per-database policy.
5. Define reference sample files that document the supported file formats.
6. Keep the first version narrow, predictable, and easy to validate.

### 3.2 Non-Goals

- Redesigning the LangGraph state to hold multiple prompts in one graph run.
- Running prompts from the file concurrently.
- Introducing batch-level persistence tables or batch-level report artifacts.
- Allowing per-record overrides for flags such as `panels`, `force`, or `budget_usd` in v1.
- Changing cache fingerprinting, template behavior, or image-generation logic.

---

## 4. Proposed Design

### 4.1 Runtime contract

The CLI must accept exactly one of the following:

- `--user-prompt <prompt>`
- `--input-file <path>`

The CLI must reject:

- neither provided
- both provided

Proposed user-facing examples:

```bash
python -m comicbook.run --user-prompt "A four-panel comic of a wandering sage at sunrise"
python -m comicbook.run --input-file ComicBook/examples/prompts.sample.json
python -m comicbook.run --input-file ComicBook/examples/prompts.sample.csv --dry-run
```

### 4.2 Architectural decision

`--input-file` mode should be implemented as a CLI-level serial batch wrapper, not as a graph redesign.

That means:

- each parsed record becomes one normal workflow invocation
- each record has one `user_prompt`
- each record produces one normal `RunState`
- each record keeps its own `run_id`, reports, logs, and image output directory

This is the preferred design because the current workflow already assumes:

- `RunState.user_prompt` is a single string
- one run maps to one `run_id`
- one run writes to `runs/<run_id>/`, `logs/<run_id>.summary.json`, and `image_output/<run_id>/`
- one SQLite database allows only one active run at a time

Keeping file support outside the graph avoids forcing changes into node contracts, persistence, or resume logic.

### 4.3 Library contract

The existing library entry point `run_once(...)` should remain single-prompt and keep its current return shape.

If code changes are made later, batch behavior should live in a separate helper such as `run_batch(...)` or remain CLI-only. The single-prompt API should not be overloaded to sometimes return a list and sometimes a single `RunState`.

---

## 5. Input File Formats

### 5.1 JSON format

Supported JSON shape:

- UTF-8 encoded text file
- top-level value must be a list
- each item must be an object
- required field: `user_prompt`
- optional field: `run_id`

Proposed schema:

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

Validation rules:

- `user_prompt` must be a string
- trimmed `user_prompt` must not be empty
- `run_id`, when present, must be a non-empty string
- duplicate `run_id` values within the same file must be rejected
- unknown fields should be rejected in v1 to keep the format explicit

### 5.2 CSV format

Supported CSV shape:

- UTF-8 encoded text file
- header row required
- required column: `user_prompt`
- optional column: `run_id`

Proposed schema:

```csv
run_id,user_prompt
sample-batch-001,"A cinematic portrait of a forest guardian in moonlight"
sample-batch-002,"A three-panel comic of a clockmaker fixing time itself"
```

Validation rules:

- `user_prompt` column must exist
- whitespace should be trimmed from every parsed cell
- `user_prompt` must not be blank after trimming
- `run_id`, when present, must not be blank
- duplicate `run_id` values within the same file must be rejected
- unsupported columns should be rejected in v1 rather than silently ignored

### 5.3 Why the first version is intentionally narrow

The first version should not accept per-row runtime overrides such as:

- `panels`
- `force`
- `budget_usd`
- `dry_run`
- `redact_prompts`

Those fields create coercion and precedence problems, especially in CSV. A narrow format keeps parsing and operator expectations simple.

---

## 6. Execution Semantics

### 6.1 Serial processing

Input-file records must be executed serially in file order.

Rationale:

- the current SQLite policy allows only one active workflow run per database file at a time
- the workflow is already designed around serial execution and deterministic artifacts
- serial file processing produces stable, understandable operator output

This means `--input-file` adds batch submission, not parallel throughput.

### 6.2 Validation timing

The CLI should fully parse and validate the input file before starting the first workflow run.

Rationale:

- malformed later rows should not surprise the operator after earlier rows already executed
- duplicate `run_id` values should be caught before any work begins
- format errors are easier to explain when reported as input validation failures instead of mid-batch runtime failures

### 6.3 Run identity

Each input-file record maps to one workflow run.

Rules:

- record-level `run_id` is optional
- if omitted, the runtime may auto-generate one using the existing UUID behavior
- CLI-level `--run-id` should be disallowed when `--input-file` is used

Why disallow CLI `--run-id` in file mode:

- the existing model treats `run_id` as one run identifier, not a batch identifier
- sharing one CLI `--run-id` across multiple records would conflict with per-run persistence and artifact paths
- allowing per-record `run_id` in the file keeps resume semantics explicit

### 6.4 Resume behavior

Resume behavior remains per run, not per batch.

Implications:

- if the file contains explicit `run_id` values, rerunning the same file can resume individual runs using the existing workflow behavior
- if the file omits `run_id`, rerunning the file creates new runs rather than resuming prior ones

This should be documented clearly because resumable batches depend on stable per-record identifiers.

---

## 7. Interaction With Existing Flags

In file mode, existing CLI flags should behave as global defaults applied to every record in the file.

| Flag | Proposed behavior in `--input-file` mode |
|---|---|
| `--dry-run` | Applied to every record |
| `--force` | Applied to every record |
| `--panels` | Applied to every record |
| `--budget-usd` | Applied per record, not as one shared batch budget |
| `--redact-prompts` | Applied to every record |
| `--run-id` | Rejected in file mode |

### 7.1 Budget semantics

`--budget-usd` should remain a per-run budget.

That means in file mode:

- each record independently checks its estimated run cost against `--budget-usd`
- the existing daily budget logic continues to accumulate across all records naturally

This avoids inventing a new batch budget model in v1.

---

## 8. Reporting and Exit Behavior

### 8.1 Per-run artifacts

Per-run artifacts remain unchanged:

- `runs/<run_id>/report.md`
- `logs/<run_id>.summary.json`
- `image_output/<run_id>/...`

No batch-level persisted artifact is required in v1.

### 8.2 Stdout summary

In file mode, the CLI should emit a batch summary to stdout after processing completes.

Suggested fields:

- `total_records`
- `succeeded`
- `partial`
- `dry_run`
- `failed`
- `input_file`
- `run_ids`

This provides a machine-readable top-level result without changing the per-run reporting contract.

### 8.3 Exit code

The overall process should exit non-zero if any of the following occur:

- input file parsing or validation fails
- any record finishes with a failing run status

The process may still continue through all valid records after an individual runtime failure, but the final exit code should reflect that the full batch was not completely successful.

---

## 9. Sample Reference Files

The implementation should add sample files that document the supported shapes.

Proposed paths:

- `ComicBook/examples/prompts.sample.json`
- `ComicBook/examples/prompts.sample.csv`

These files should:

- include at least two prompts each
- demonstrate optional `run_id`
- be safe to run locally
- be referenced from operator-facing documentation later

---

## 10. Implementation Impact

Expected code impact is concentrated in the CLI and input-loading boundary:

- `ComicBook/comicbook/run.py`
- possibly a new small helper module for parsing input files
- tests covering CLI parsing, JSON/CSV validation, and batch execution behavior

No graph-node redesign is expected if this design is followed.

Likely unaffected modules:

- `comicbook.graph`
- `comicbook.nodes.*`
- `comicbook.fingerprint`
- `comicbook.image_client`
- persistence schema in `comicbook.db`

---

## 11. Risks and Tradeoffs

### 11.1 Throughput remains linear

Large input files will be slow because both the workflow and the database policy are serial by design. This is acceptable for v1 because the goal is submission convenience, not higher throughput.

### 11.2 Resume is strongest when `run_id` is provided

Auto-generated `run_id` values are convenient for ad hoc file runs but make reruns non-resumable at the batch level. Operators who care about resumability should supply `run_id` values in the file.

### 11.3 Narrow schemas reduce ambiguity

Rejecting unknown columns and fields is stricter than some CSV/JSON tools, but it prevents silent misconfiguration and keeps future schema expansion deliberate.

---

## 12. ADR Assessment

An ADR is not required if this enhancement remains:

- a CLI input-format extension
- a serial wrapper around the existing single-prompt workflow
- compatible with the current per-run persistence and reporting model

An ADR should be created later if the scope expands into any of the following:

- true multi-prompt graph state
- batch-level persistence or batch-level run IDs
- shared batch reporting artifacts
- per-record override schemas with precedence rules

---

## 13. Acceptance Criteria for Implementation

The enhancement is ready for implementation when the team agrees on the following acceptance targets:

1. The CLI accepts exactly one prompt source: positional prompt or `--input-file`.
2. JSON files with a list of `{user_prompt, optional run_id}` records are supported.
3. CSV files with `user_prompt` and optional `run_id` columns are supported.
4. Invalid file shape, blank prompts, duplicate `run_id` values, and unsupported fields or columns fail validation before execution begins.
5. File records execute serially in file order.
6. Each record produces its own normal workflow run and normal report artifacts.
7. `--dry-run`, `--force`, `--panels`, `--budget-usd`, and `--redact-prompts` apply uniformly to every record in file mode.
8. `--run-id` is rejected when `--input-file` is used.
9. Sample JSON and CSV files are added under `ComicBook/examples/`.
10. Existing single-prompt CLI and library behavior remains intact.

---

## 14. Recommended Next Step

Implement the enhancement as a CLI-focused change with tests first, then update the business and developer docs alongside the sample files. That follow-up work will trigger the full documentation triad update because it changes the user-visible runtime surface.
