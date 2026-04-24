# Template Upload Workflow

## Status and scope

- Workflow delivery status: implemented
- Last updated: 2026-04-24
- Latest mocked validation result: `113 passed`
- Optional live Azure smoke: not run in this session

This workflow adds a second LangGraph entry point to the `ComicBook` package for importing template rows into the shared SQLite template library.

Covered runtime surface:

- CLI entry point: `python -m comicbook.upload_run`
- library helper: `from comicbook import upload_templates`
- graph assembly: `comicbook.upload_graph`
- report/log finalization: `comicbook.nodes.upload_summarize`

## Runtime entry points

### CLI

From `ComicBook/`:

```bash
uv run python -m comicbook.upload_run --help
```

Supported surface:

- one source only: positional `source_file` or `--stdin`
- `--dry-run`
- `--no-backfill`
- `--allow-missing-optional` (requires `--no-backfill`)
- `--budget-usd <float>`
- `--redact-style-text-in-logs`
- `--allow-external-path`

Exit-code mapping:

- `0`: success, partial success, or dry run after normal workflow completion
- `3`: hard file/input error surfaced as `ValueError`
- `4`: import lock contention via `RunLockError`
- `5`: unhandled workflow/runtime failure after startup

### Library helper

Primary helper:

```python
from comicbook import upload_templates

state = upload_templates(
    source_file="templates.json",
    dry_run=True,
)
```

Important runtime notes:

- `comicbook.__init__` now exposes `upload_templates` lazily so `python -m comicbook.upload_run` does not emit a runpy warning.
- `comicbook.runtime_deps` holds the shared managed-dependency helpers that both `run.py` and `upload_run.py` reuse.

## Graph shape

Compiled order from `comicbook.upload_graph`:

1. `upload_load_file`
2. `upload_parse_and_validate`
3. `upload_resume_filter`
4. `upload_backfill_metadata`
5. `upload_decide_write_mode`
6. `upload_persist`
7. conditional same-run deferred retry preparation
8. `upload_decide_write_mode` again for deferred rows
9. `upload_persist` again for deferred rows
10. `upload_summarize`

Why the retry path exists:

- rows that reference a `supersedes_id` expected later in the same file can defer once
- after one same-run retry pass, unresolved targets are downgraded to warnings and stored as `NULL`

## State contracts

Primary types in `comicbook.state`:

- `TemplateImportRow`
- `TemplateImportRowResult`
- `ImportRunState`
- `ImportRowStatus = Literal["inserted", "updated", "failed", "skipped_resume", "skipped_duplicate", "dry_run_ok"]`
- `ImportWriteMode = Literal["insert", "update", "skip", "defer"]`

Important `ImportRunState` fields:

- input/source: `import_run_id`, `source_file_path`, `stdin_text`, `source_file_hash`, `input_version`
- controls: `dry_run`, `no_backfill`, `allow_missing_optional`, `allow_external_path`, `budget_usd`, `redact_style_text_in_logs`
- row flow: `raw_rows`, `parsed_rows`, `rows_to_process`, `deferred_rows`, `rows_skipped_by_resume`, `row_results`
- accounting: `usage`, `errors`, `started_at`, `ended_at`, `run_status`, `report_path`

Important row-level conventions:

- `tags: []` is intentional and does not trigger backfill
- `summary` backfill is triggered for missing, `null`, or blank strings
- `stdin_text` must be present in the state schema so the graph can preserve stdin-driven imports end to end

## Persistence model

Upload-specific persistence remains inside `comicbook.db`.

Key import helpers:

- `acquire_import_lock(...)`
- `finalize_import_run(...)`
- `get_import_run(...)`
- `record_import_row_result(...)`
- `get_template_by_id(...)`
- `update_template_in_place(...)`
- `count_prompt_rows_for_template_hash(...)`

Upload-specific durable tables:

- `import_runs`
- `import_row_results`

Important persistence behavior:

- import locking is separate from the primary image-workflow `runs` lock
- resume lookup is based on prior terminal success for the same `source_file_hash` and `row_index`
- zero-diff updates become `skipped_duplicate`
- `update_template_in_place(...)` recomputes `style_text_hash`
- row results persist requested/persisted supersedes values, warnings, retry counts, diffs, and any raw backfill text used for auditability

Watchpoint:

- `count_prompt_rows_for_template_hash(...)` currently supports fingerprint-drift reporting by scanning persisted prompt rows tied to the current template hash shape; revisit only if report requirements become stricter.

## Module responsibilities

### `comicbook/upload_run.py`

- CLI parsing and exit-code mapping
- stdin vs file-source handling
- import-lock acquisition
- invocation of `run_upload_workflow(...)`
- final stdout JSON

### `comicbook/runtime_deps.py`

- shared managed dependency construction for CLI/library entry points
- config loading fallback when caller did not provide `Deps`
- pricing metadata loading
- cleanup of managed DB and HTTP client resources

### `comicbook/nodes/upload_load_file.py`

- source-file resolution and UTF-8 reading
- bare-array vs versioned-envelope parsing
- file-size guard
- current-working-tree path policy unless `allow_external_path` is enabled

### `comicbook/nodes/upload_parse_and_validate.py`

- row normalization
- required-field validation
- warning capture for overridden/ignored fields
- row-limit enforcement

### `comicbook/nodes/upload_resume_filter.py`

- resume skip-set lookup by source hash and row index
- carry-forward of retry count from prior attempts

### `comicbook/nodes/upload_backfill_metadata.py`

- structured metadata backfill through the shared Responses transport
- serial execution, retry handling, and budget guard
- optional offline fallback path with `--no-backfill --allow-missing-optional`

### `comicbook/nodes/upload_decide_write_mode.py`

- validation skip routing
- insert vs update detection
- defer decisions for same-file supersedes chains

### `comicbook/nodes/upload_persist.py`

- insert/update/skipped-duplicate execution
- diff construction for updates
- row-result persistence alongside template writes
- style-text preview redaction when requested

### `comicbook/nodes/upload_summarize.py`

- final run counts and terminal status
- `runs/<import_run_id>/import_report.md`
- `logs/<import_run_id>.import.jsonl`
- updated-row diff sections and unresolved-supersedes warning sections
- finalization of `import_runs` counters and estimated backfill cost totals

## Reporting and observability

Markdown report includes:

- run metadata
- per-status counts
- row-result table
- update diff sections
- unresolved supersedes warning section when applicable

Structured log includes:

- one JSONL event per row result
- mapped event names such as `template_inserted`, `template_updated`, `template_skipped_duplicate`, `row_skipped_resume`, and row-failure variants
- a terminal `import_finished` event with final usage totals

## Local setup and verification

Work from `ComicBook/`.

Required configuration remains the same Azure env set used by the image workflow:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`
- `AZURE_OPENAI_IMAGE_DEPLOYMENT`

Upload-relevant optional config:

- `COMICBOOK_IMPORT_MAX_ROWS_PER_FILE`
- `COMICBOOK_IMPORT_MAX_FILE_BYTES`
- `COMICBOOK_IMPORT_ALLOW_EXTERNAL_PATH`
- `COMICBOOK_IMPORT_BACKFILL_MODEL`
- `COMICBOOK_DB_PATH`
- `COMICBOOK_RUNS_DIR`
- `COMICBOOK_LOGS_DIR`

Recommended closeout verification path:

```bash
uv run python -m pytest -q tests/test_upload_graph.py tests/test_upload_run_cli.py
uv run python -m pytest -q
```

Session evidence for this closeout slice:

- focused upload runtime-surface scope: `14 passed`
- full mocked suite: `113 passed`
- verified CLI examples:
  - `uv run python -m comicbook.upload_run --allow-external-path ../docs/planning/template-upload-workflow/sample_input.json`
  - `uv run python -m comicbook.upload_run --stdin < ../docs/planning/template-upload-workflow/sample_input.json`

## Debugging and maintenance notes

- If stdin imports fail unexpectedly, confirm `stdin_text` is present in `ImportRunState` and preserved through graph invocation.
- If `python -m comicbook.upload_run` emits a runpy import warning again, re-check the lazy package export in `comicbook.__init__`.
- If path-based imports fail in local development, confirm whether the file is outside the current working tree and whether `--allow-external-path` or `COMICBOOK_IMPORT_ALLOW_EXTERNAL_PATH=1` is appropriate.
- If a rerun does not skip completed rows, inspect `import_row_results` for the same `source_file_hash` and `row_index` and confirm the prior status was a terminal success.
- If update reports look incomplete, inspect the row's computed diff plus the persisted `style_text_hash` change in `upload_persist.py`.
- Keep the planning, business, and developer docs aligned on the same workflow slug: `template-upload-workflow`.

## Current limitations and watchpoints

- Live Azure smoke validation remains intentionally opt-in and was not executed in this session.
- The one-row atomicity intent should continue to be watched if `db.py` changes later, especially around template write + row-result persistence sequencing.
- The current path policy is based on the invoker's current working tree; sample files outside that tree require `--allow-external-path`.
- No ADR was needed for this implementation because the shipped shape stayed within the approved persistence, locking, and reporting design.
