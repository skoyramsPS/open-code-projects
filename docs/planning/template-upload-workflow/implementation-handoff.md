# Implementation Handoff: Template Upload Workflow

- Status: TG1 complete, TG2 complete, TG3 complete, TG4 complete, TG5 complete, TG6 pending
- Last updated: 2026-04-24
- Implementation guide: `docs/planning/template-upload-workflow/implementation.md`
- Planning index: `docs/planning/template-upload-workflow/index.md`

## Current status summary

This handoff tracks the standalone implementation guide for the template-upload workflow.

Current repository state:

- planning exists at `docs/planning/template-upload-workflow/plan.md`
- canonical sample input exists at `docs/planning/template-upload-workflow/sample_input.json`
- shared upload workflow scaffolding now exists in `ComicBook/comicbook/state.py`, `config.py`, and `db.py`
- front-half upload nodes now exist for file loading, row normalization, and resume filtering
- metadata backfill prompt/schema helpers now exist in `ComicBook/comicbook/metadata_prompts.py`
- `ComicBook/comicbook/nodes/upload_backfill_metadata.py` exists
- `ComicBook/comicbook/nodes/upload_decide_write_mode.py` exists
- `ComicBook/comicbook/nodes/upload_persist.py` exists
- `ComicBook/comicbook/nodes/upload_summarize.py` exists
- `ComicBook/comicbook/upload_graph.py` exists
- `ComicBook/comicbook/upload_run.py` exists
- `ComicBook/comicbook.__init__` now re-exports `upload_templates`
- `ComicBook/comicbook/nodes/upload_load_file.py` exists
- `ComicBook/comicbook/nodes/upload_parse_and_validate.py` exists
- `ComicBook/comicbook/nodes/upload_resume_filter.py` exists
- upload-specific contract tests exist under `ComicBook/tests/`
- there are no workflow-specific business or developer docs yet for this workflow

In short: the workflow runtime surface now exists end-to-end through `upload_templates(...)` and `python -m comicbook.upload_run`, and the remaining work is final verification plus the required documentation triad and index sync.

## TaskGroup status table

| TaskGroup | Title | Status | Notes |
|---|---|---|---|
| TG1 | Lock the contract with focused failing tests | completed | Added upload contract tests and verified they fail on missing upload modules plus missing import DB contracts. |
| TG2 | Add shared persistence, config, and state scaffolding | completed | Added import state TypedDicts/statuses, upload guardrail config fields, import tables/indexes, import lock helpers, and new DAO helpers with focused regression coverage. |
| TG3 | Implement file ingest, validation, and resumability | completed | Added `upload_load_file`, `upload_parse_and_validate`, and `upload_resume_filter` with direct pytest coverage including stdin, validation behavior, row-limit enforcement, and resume retry-count carry-forward. |
| TG4 | Implement backfill, write-mode routing, and persistence | completed | Added metadata backfill, write-mode routing, and persistence nodes with focused pytest coverage for insert/update/skip/duplicate and backfill guardrail paths. |
| TG5 | Wire the graph, CLI, package export, and reporting | completed | Added upload graph, summarize/report node, CLI/library entry point, package re-export, and focused runtime-surface tests including lock/error mapping. |
| TG6 | Verification, documentation triad, and closeout | pending | Business and developer docs for this workflow have not been created. |

## What was created or updated in this planning session

- Created `docs/planning/template-upload-workflow/implementation.md` as the standalone execution guide for the delivery team.
- Created `docs/planning/template-upload-workflow/implementation-handoff.md` as the resumable status ledger for future `/implement-next` work.
- Created `docs/planning/template-upload-workflow/index.md` to keep the planning-folder documentation indexed.
- Updated `docs/planning/index.md` to include the new workflow planning folder.

## What was created or updated in the first implementation slice

- Added `ComicBook/tests/test_upload_run_cli.py` for the upload CLI argument contract.
- Added `ComicBook/tests/test_upload_load_file.py` for source loading, bare-array/envelope parsing, and top-level shape validation.
- Added `ComicBook/tests/test_upload_parse_and_validate.py` for row normalization, required-field validation, and `created_by_run` override warnings.
- Added `ComicBook/tests/test_upload_resume_filter.py` for resume semantics and retry-count carry-forward.
- Added `ComicBook/tests/test_upload_persist.py` for zero-diff `skipped_duplicate` handling and unresolved `supersedes_id` null fallback.
- Extended `ComicBook/tests/test_db.py` with import-schema and import-lock expectations.
- Synced the local `ComicBook` dev environment so `pytest` is available for narrow-scope verification.

## Completed work from this session

- Selected the remaining **TG5** runtime-surface cluster from the handoff because it was still the earliest unfinished, tightly related, commit-sized slice after the graph/report sub-slice.
- Added `ComicBook/comicbook/upload_run.py` with:
  - CLI argument parsing for the upload workflow surface
  - `upload_templates(...)` library helper using the locked signature from the guide
  - managed dependency lifecycle when `deps is None`
  - import-lock acquisition before graph execution
  - finalization of running import records on unhandled exceptions
  - exit-code mapping in `main(...)`
  - stdout JSON summary for successful and partial runs
- Updated `ComicBook/comicbook/__init__.py` to re-export `upload_templates`.
- Extended `ComicBook/tests/test_upload_run_cli.py` with focused coverage for:
  - additional runtime-surface flags
  - package re-export and successful library-helper execution with provided deps
  - stdin-to-helper CLI wiring
  - import-lock error mapping to exit code `4`

## Files changed this session

- `ComicBook/comicbook/upload_run.py`
- `ComicBook/comicbook/__init__.py`
- `ComicBook/tests/test_upload_run_cli.py`
- `docs/planning/template-upload-workflow/implementation-handoff.md`

## Tests run this session

From `ComicBook/`:

1. `uv run python -m pytest -q tests/test_db.py tests/test_config.py`
   - initial result before implementation: failed as expected on missing import schema/helpers and missing upload state symbols
   - final result after implementation: **17 passed**
2. `uv run python -m pytest -q tests/test_db.py tests/test_config.py tests/test_node_load_templates.py tests/test_node_ingest_summarize.py tests/test_budget_guard.py`
   - final focused regression result: **26 passed**
3. `uv run python -m pytest -q tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py`
   - initial result before implementation: failed as expected on missing upload node modules
   - final result after implementation: **9 passed**
4. `uv run python -m pytest -q tests/test_db.py tests/test_config.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_node_load_templates.py tests/test_node_ingest_summarize.py`
   - final broadened regression result: **30 passed**
5. `uv run python -m pytest -q tests/test_upload_backfill_metadata.py`
   - final focused backfill result: **6 passed**
6. `uv run python -m pytest -q tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_router_node.py tests/test_router_validation.py tests/test_budget_guard.py`
   - final broadened backfill/router regression result: **28 passed**
7. `uv run python -m pytest -q tests/test_upload_persist.py tests/test_upload_decide_write_mode.py`
   - initial result before implementation: failed as expected on missing persistence/write-mode modules
   - final focused persistence result: **9 passed**
8. `uv run python -m pytest -q tests/test_upload_persist.py tests/test_upload_decide_write_mode.py tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_db.py tests/test_config.py`
   - final broadened row-flow regression result: **41 passed**
9. `uv run python -m pytest -q tests/test_upload_graph.py`
   - initial result before implementation: failed as expected on missing `comicbook.upload_graph`
   - final focused graph/report result: **3 passed**
10. `uv run python -m pytest -q tests/test_upload_graph.py tests/test_upload_persist.py tests/test_upload_decide_write_mode.py tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py`
    - final broadened graph + row-flow regression result: **27 passed**
11. `uv run python -m pytest -q tests/test_upload_graph.py tests/test_upload_persist.py tests/test_upload_decide_write_mode.py tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_db.py tests/test_config.py`
    - final extended graph regression result: **44 passed**
12. `uv run python -m pytest -q tests/test_upload_run_cli.py tests/test_upload_graph.py`
    - final focused runtime-surface result: **12 passed**
13. `uv run python -m pytest -q tests/test_upload_run_cli.py tests/test_upload_graph.py tests/test_upload_persist.py tests/test_upload_decide_write_mode.py tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_db.py tests/test_config.py`
    - final extended runtime-surface regression result: **53 passed**

## Documentation updated this session

- Updated this handoff document to reflect TG5 completion, verification evidence, and the next recommended slice.
- Reviewed the docs-update gate for this slice. The workflow now has a user-facing CLI/library runtime surface, so the full business/developer documentation triad is now mandatory before the work can be called complete overall. Per the implementation guide sequence, those documentation updates remain the next TG6 slice; no new indexes or ADRs were added in this runtime-surface increment itself.

## Blockers or open questions

- No blocker prevents TG6.
- The `count_prompt_rows_for_template_hash(...)` helper currently counts prompts by scanning persisted prompt rows for template-id membership tied to the current template hash. Revisit only if later fingerprint-drift/report requirements prove a stricter query shape is needed.
- The backfill budget guard currently uses a best-effort pre-call estimate derived from payload size plus router pricing keys; if later acceptance testing requires a different estimation heuristic, document that before closeout.
- `upload_persist.py` currently relies on existing DAO helpers that each commit independently. That is enough for the current focused tests, but the intended one-row atomicity guarantee should be re-verified when wiring the graph and summarize/finalization layer in TG5.
- An opt-in live Azure smoke test is still pending and should only run in TG6 when credentials are available.

## Locked implementation decisions from the guide

These items were ambiguous or contradictory in `plan.md` and are now locked for implementation:

1. CLI module is `python -m comicbook.upload_run`; library helper is `upload_templates(...)`.
2. Input accepts either a bare array or `{ "version": 1, "templates": [...] }`.
3. `tags: []` is intentional and does not trigger backfill.
4. Zero-diff updates end as `skipped_duplicate`, not `updated`.
5. `supersedes_id` uses a two-phase resolution pass and falls back to `NULL` with a warning if still unresolved.
6. `import_runs` must include `pid` and `host` for lock ownership.
7. `import_row_results` stores one terminal row result per row per import run and includes `retry_count`.
8. v1 uses one transaction per row; batched commits are deferred.
9. Existing `runs/` and `logs/` roots are reused; no new import-output root is introduced.

## Unresolved assumptions or watchpoints

These are not blockers for starting TG6, but they should be watched during implementation:

- The final code may show that `router_llm.py` needs a tiny shared helper for generic schema calls. If so, keep that change additive and do not disturb the image-router contract.
- Fingerprint-drift reporting depends on the exact prompt-table lookup shape in `db.py`; verify it with tests before finalizing report language.
- If the live Azure smoke test reveals transport behavior not captured by current mocks, update the implementation guide or developer docs during TG6.
- If the implementation materially changes concurrency or persistence beyond this guide, add an ADR before calling the work complete.

## Exact next recommended slice

- Start **TG6** from `docs/planning/template-upload-workflow/implementation.md`.
- Recommended scope: complete the closeout slice if it stays manageable in one session:
  1. run the focused then broader pytest scopes
  2. add `docs/business/template-upload-workflow/index.md`
  3. add `docs/developer/template-upload-workflow/index.md`
  4. update `docs/index.md`, `docs/business/index.md`, and `docs/developer/index.md`
  5. verify sample commands/examples against the shipped runtime surface
  6. decide whether an ADR is needed; add one only if the final implementation materially deviates from the approved persistence/concurrency shape
- Keep the optional live Azure smoke test separate if credentials are not available in the session.

## Suggested verification path for the next implementation slice

When TG6 is in progress, follow the guide's closeout progression from focused to broad:

```bash
uv run python -m pytest -q tests/test_upload_graph.py tests/test_upload_run_cli.py
uv run python -m pytest -q
```

Run it from `ComicBook/`. Only after the runtime-surface scope is green should you broaden to the full repo test suite and complete the documentation triad updates.

## Documentation gate note

- The docs-update gate was reviewed for this TG5 runtime-surface slice.
- This slice created the user-facing CLI/library surface, so the documentation gate is now fully active for closeout.
- The required business/developer docs and index maintenance remain pending and must be completed in TG6 before this workflow can be marked complete.

## Permission checkpoint

Implementation must **not** start automatically from this handoff.

Please review the guide and confirm whether you want to proceed with:

`/implement-next docs/planning/template-upload-workflow/implementation.md docs/planning/template-upload-workflow/implementation-handoff.md`

Do not begin code, test, or runtime-document changes for this workflow until the user explicitly approves that next step.

## Session log

### 2026-04-24

- Inspected the planning document, current planning indexes, related image-workflow implementation docs, and the current `ComicBook` runtime modules.
- Confirmed the repository initially had no upload-workflow code, tests, or workflow-specific runtime docs.
- Authored the standalone implementation guide and seeded this handoff file from the current repository state.
- Added TG1 contract tests for the upload CLI, load-file node, parse/validate node, resume filter, persist node, and import DB contracts.
- Synced the local dev environment with `uv sync --extra dev` so `pytest` is available.
- Verified the narrow TG1 pytest scope fails for the intended reasons: missing upload modules and missing import DB/shared-contract implementation.

### 2026-04-24 — TG2 implementation slice

- Reviewed the implementation guide, current handoff, existing shared runtime modules, and the local `implementation-slice-guard` instructions to choose the next eligible slice.
- Selected the full TG2 slice because the remaining work was a single shared-contract increment covering `state.py`, `config.py`, `db.py`, and focused tests.
- Added upload state aliases/TypedDicts, upload config guardrails, import persistence schema/indexes, import lock helpers, and DAO helpers.
- Extended `tests/test_config.py` and `tests/test_db.py` to cover the new contracts directly.
- Verified the final TG2-focused scope passes:
  - `uv run python -m pytest -q tests/test_db.py tests/test_config.py`
  - `uv run python -m pytest -q tests/test_db.py tests/test_config.py tests/test_node_load_templates.py tests/test_node_ingest_summarize.py tests/test_budget_guard.py`

### 2026-04-24 — TG3 implementation slice

- Reviewed the implementation guide, current handoff, existing upload tests, and the local `implementation-slice-guard` instructions to choose the next eligible slice.
- Selected the full TG3 slice because all remaining work stayed inside three adjacent node modules with direct unit-style pytest coverage and no graph wiring.
- Confirmed the existing TG3 test scope initially failed on missing modules:
  - `uv run python -m pytest -q tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py`
- Added the three front-half upload nodes and expanded tests for stdin input and row-limit enforcement.
- Verified the final TG3-focused scope passes:
  - `uv run python -m pytest -q tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py`
  - `uv run python -m pytest -q tests/test_db.py tests/test_config.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_node_load_templates.py tests/test_node_ingest_summarize.py`

### 2026-04-24 — TG4 backfill sub-slice

- Reviewed the implementation guide, current handoff, existing repository state, and the local `implementation-slice-guard` instructions to choose the next eligible slice after TG3.
- Kept the handoff's recommended first TG4 cluster because it remained the earliest unfinished, foundational, commit-sized increment.
- Added the metadata backfill prompt/schema module plus an additive generic structured-response helper in `router_llm.py`.
- Implemented `upload_backfill_metadata.py` with success, retry, budget-guard, offline fallback, and circuit-breaker behavior.
- Added focused unit tests for backfill success/failure and guardrail paths.
- Verified the final TG4 backfill scope passes:
  - `uv run python -m pytest -q tests/test_upload_backfill_metadata.py`
  - `uv run python -m pytest -q tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_router_node.py tests/test_router_validation.py tests/test_budget_guard.py`

### 2026-04-24 — TG4 persistence sub-slice

- Reviewed the implementation guide, current handoff, existing persistence tests, and the local `implementation-slice-guard` instructions to choose the next eligible slice after the TG4 backfill cluster.
- Kept the handoff's recommended second TG4 cluster because it remained the correct earliest unfinished, commit-sized increment.
- Added `upload_decide_write_mode.py` and `upload_persist.py` plus focused tests for write-mode decisions and persistence outcomes.
- Confirmed the focused persistence scope initially failed on missing modules:
  - `uv run python -m pytest -q tests/test_upload_persist.py tests/test_upload_decide_write_mode.py`
- Verified the final TG4 persistence scope passes:
  - `uv run python -m pytest -q tests/test_upload_persist.py tests/test_upload_decide_write_mode.py`
  - `uv run python -m pytest -q tests/test_upload_persist.py tests/test_upload_decide_write_mode.py tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_db.py tests/test_config.py`

### 2026-04-24 — TG5 graph/report sub-slice

- Reviewed the implementation guide, current handoff, existing runtime modules, and the local `implementation-slice-guard` instructions to choose the next eligible slice after TG4 completion.
- Kept the handoff's recommended first TG5 cluster because it remained the correct earliest unfinished, commit-sized increment.
- Added `upload_summarize.py`, `upload_graph.py`, and focused graph/report integration tests.
- Adjusted deferred-row handling so the graph can perform one same-run supersedes retry pass before summarizing.
- Confirmed the focused graph scope initially failed on missing `comicbook.upload_graph`:
  - `uv run python -m pytest -q tests/test_upload_graph.py`
- Verified the final TG5 graph/report scope passes:
  - `uv run python -m pytest -q tests/test_upload_graph.py`
  - `uv run python -m pytest -q tests/test_upload_graph.py tests/test_upload_persist.py tests/test_upload_decide_write_mode.py tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py`
  - `uv run python -m pytest -q tests/test_upload_graph.py tests/test_upload_persist.py tests/test_upload_decide_write_mode.py tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_db.py tests/test_config.py`

### 2026-04-24 — TG5 runtime-surface sub-slice

- Reviewed the implementation guide, current handoff, existing CLI tests, and the local `implementation-slice-guard` instructions to choose the next eligible slice after the TG5 graph/report cluster.
- Kept the handoff's recommended remaining TG5 runtime-surface cluster because it remained the correct earliest unfinished, commit-sized increment.
- Added `upload_run.py`, package re-export support in `__init__.py`, and focused runtime-surface tests.
- Verified the focused runtime-surface scope passes:
  - `uv run python -m pytest -q tests/test_upload_run_cli.py tests/test_upload_graph.py`
- Verified the extended runtime-surface regression scope passes:
  - `uv run python -m pytest -q tests/test_upload_run_cli.py tests/test_upload_graph.py tests/test_upload_persist.py tests/test_upload_decide_write_mode.py tests/test_upload_backfill_metadata.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_db.py tests/test_config.py`

*End of handoff.*
