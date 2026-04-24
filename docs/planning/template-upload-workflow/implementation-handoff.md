# Implementation Handoff: Template Upload Workflow

- Status: TG1 complete, TG2 complete, TG3 complete, TG4 complete, TG5 complete, TG6 complete
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
- `ComicBook/comicbook/runtime_deps.py` now holds shared managed-runtime setup/cleanup helpers for both CLI entry points
- `ComicBook/comicbook/nodes/upload_load_file.py` exists
- `ComicBook/comicbook/nodes/upload_parse_and_validate.py` exists
- `ComicBook/comicbook/nodes/upload_resume_filter.py` exists
- upload-specific contract tests exist under `ComicBook/tests/`
- workflow-specific business and developer docs now exist under `docs/business/template-upload-workflow/` and `docs/developer/template-upload-workflow/`

In short: the upload workflow is now implemented, documented, and verified through the mocked test suite. No further `/implement-next` slice remains for this guide unless the implementation guide is expanded later.

## TaskGroup status table

| TaskGroup | Title | Status | Notes |
|---|---|---|---|
| TG1 | Lock the contract with focused failing tests | completed | Added upload contract tests and verified they fail on missing upload modules plus missing import DB contracts. |
| TG2 | Add shared persistence, config, and state scaffolding | completed | Added import state TypedDicts/statuses, upload guardrail config fields, import tables/indexes, import lock helpers, and new DAO helpers with focused regression coverage. |
| TG3 | Implement file ingest, validation, and resumability | completed | Added `upload_load_file`, `upload_parse_and_validate`, and `upload_resume_filter` with direct pytest coverage including stdin, validation behavior, row-limit enforcement, and resume retry-count carry-forward. |
| TG4 | Implement backfill, write-mode routing, and persistence | completed | Added metadata backfill, write-mode routing, and persistence nodes with focused pytest coverage for insert/update/skip/duplicate and backfill guardrail paths. |
| TG5 | Wire the graph, CLI, package export, and reporting | completed | Added upload graph, summarize/report node, CLI/library entry point, package re-export, and focused runtime-surface tests including lock/error mapping. |
| TG6 | Verification, documentation triad, and closeout | completed | Added business/developer docs plus index sync, fixed closeout regressions around shared runtime imports and stdin state preservation, verified documented CLI commands, and finished the mocked closeout suite. |

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

- Selected the full remaining **TG6** closeout slice because the unfinished work was one cohesive verification-and-documentation pass that fit a single commit-sized delivery.
- Ran the focused then full pytest progression and found closeout regressions that the earlier narrow scopes had not exposed:
  - `comicbook.upload_run` imported shared runtime helpers from `comicbook.run`, violating the shared-module boundary and causing the repo-wide architecture test to fail
  - stdin-driven imports failed end-to-end because `stdin_text` was missing from `ImportRunState`
  - `--allow-external-path` existed at the CLI/config surface but path-policy enforcement was still missing in `upload_load_file`
- Fixed the closeout regressions by:
  - extracting shared managed-runtime setup/cleanup into new `ComicBook/comicbook/runtime_deps.py`
  - making `comicbook.__init__` lazily expose `upload_templates` so `python -m comicbook.upload_run` no longer emits the runpy warning
  - adding `stdin_text` to `ImportRunState`
  - enforcing the current-working-tree path policy in `upload_load_file`, with explicit opt-in via `--allow-external-path`
- Extended focused regression coverage for:
  - lazy package re-export behavior
  - end-to-end stdin use through `upload_templates(...)`
  - external-path rejection in `upload_load_file`
- Added the required documentation triad closeout pieces for this workflow:
  - `docs/business/template-upload-workflow/index.md`
  - `docs/developer/template-upload-workflow/index.md`
  - index sync in `docs/index.md`, `docs/business/index.md`, and `docs/developer/index.md`
- Verified the documented CLI examples against the shipped runtime surface using the checked-in sample input.

## Files changed this session

- `ComicBook/comicbook/runtime_deps.py`
- `ComicBook/comicbook/run.py`
- `ComicBook/comicbook/upload_run.py`
- `ComicBook/comicbook/__init__.py`
- `ComicBook/comicbook/state.py`
- `ComicBook/comicbook/nodes/upload_load_file.py`
- `ComicBook/tests/test_upload_load_file.py`
- `ComicBook/tests/test_upload_graph.py`
- `ComicBook/tests/test_upload_run_cli.py`
- `docs/business/template-upload-workflow/index.md`
- `docs/developer/template-upload-workflow/index.md`
- `docs/index.md`
- `docs/business/index.md`
- `docs/developer/index.md`
- `docs/planning/template-upload-workflow/implementation-handoff.md`

## Tests run this session

From `ComicBook/`:

1. `uv run python -m pytest -q tests/test_upload_graph.py tests/test_upload_run_cli.py`
   - initial TG6 focused result before the new closeout fixes: **12 passed**
2. `uv run python -m pytest -q`
   - first full closeout run exposed a repo-wide regression: **1 failed, 110 passed**
   - failing check: `tests/test_example_single_portrait.py::test_shared_modules_do_not_import_workflow_specific_graph_or_run_modules`
3. `uv run python -m pytest -q tests/test_upload_run_cli.py -k stdin_text`
   - regression test added for stdin end-to-end flow; initial result before the state fix: **1 failed**
4. `uv run python -m pytest -q tests/test_upload_run_cli.py -k lazy`
   - regression test added for lazy package re-export; initial result before the `__init__` fix: **1 failed**
5. `uv run python -m pytest -q tests/test_upload_load_file.py -k external_path`
   - regression test added for path-policy enforcement; initial result before the `upload_load_file` fix: **1 failed**
6. `uv run python -m pytest -q tests/test_upload_run_cli.py -k "lazy or stdin or reexport"`
   - focused runtime-surface regression result after fixes: **6 passed**
7. `uv run python -m pytest -q tests/test_upload_load_file.py tests/test_upload_run_cli.py`
   - focused file-ingest + CLI result after path-policy updates: **16 passed**
8. `uv run python -m pytest -q tests/test_upload_load_file.py tests/test_upload_run_cli.py tests/test_upload_graph.py`
   - final focused upload closeout scope: **19 passed**
9. `uv run python -m pytest -q`
   - final broadened mocked suite after all TG6 fixes: **114 passed**
10. Verified documented CLI examples from `ComicBook/` with temporary local env values:
    - `uv run python -m comicbook.upload_run --allow-external-path ../docs/planning/template-upload-workflow/sample_input.json` → **succeeded**
    - `uv run python -m comicbook.upload_run --stdin < ../docs/planning/template-upload-workflow/sample_input.json` → **succeeded**

## Documentation updated this session

- Docs-update gate triggered: this is a significant workflow change with new CLI/library/runtime/persistence behavior.
- Added `docs/business/template-upload-workflow/index.md`.
- Added `docs/developer/template-upload-workflow/index.md`.
- Updated `docs/index.md`, `docs/business/index.md`, and `docs/developer/index.md`.
- Updated this handoff document to record TG6 completion.
- No ADR was added because the shipped implementation still matches the approved persistence, locking, and reporting design closely enough that no new architectural decision record was required.

## Blockers or open questions

- No blocker remains for the implementation guide itself.
- The `count_prompt_rows_for_template_hash(...)` helper currently counts prompts by scanning persisted prompt rows for template-id membership tied to the current template hash. Revisit only if later fingerprint-drift/report requirements prove a stricter query shape is needed.
- The backfill budget guard currently uses a best-effort pre-call estimate derived from payload size plus router pricing keys; if later acceptance testing requires a different estimation heuristic, document that before closeout.
- `upload_persist.py` currently relies on existing DAO helpers that each commit independently. The mocked closeout suite is green, but keep watching this if later work needs a stricter explicit one-row transaction boundary.
- An opt-in live Azure smoke test remains separate from the default mocked suite and should only run with explicit user approval and real credentials.

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

These are not blockers after TG6 closeout, but they should be watched in later follow-up work:

- The final code may show that `router_llm.py` needs a tiny shared helper for generic schema calls. If so, keep that change additive and do not disturb the image-router contract.
- Fingerprint-drift reporting depends on the exact prompt-table lookup shape in `db.py`; verify it with tests before finalizing report language.
- If the live Azure smoke test reveals transport behavior not captured by current mocks, update the implementation guide or developer docs during TG6.
- If the implementation materially changes concurrency or persistence beyond this guide, add an ADR before calling the work complete.

## Exact next recommended slice

- No further `/implement-next` slice remains for `docs/planning/template-upload-workflow/implementation.md`.
- Optional follow-up outside the current implementation guide closeout:
  1. run one explicitly approved live Azure smoke import with real credentials
  2. record that evidence in this handoff if you want operational proof beyond the mocked suite
  3. optionally run a separate workflow-readiness or release-readiness review if the workflow is about to ship externally

## Suggested verification path for any future follow-up

If a later follow-up changes the upload workflow again, repeat the closeout progression from focused to broad:

```bash
uv run python -m pytest -q tests/test_upload_load_file.py tests/test_upload_run_cli.py tests/test_upload_graph.py
uv run python -m pytest -q
```

If the follow-up includes real Azure traffic, keep that smoke run separate and document the exact command, cost assumptions, and result in this handoff.

## Documentation gate note

- The docs-update gate was triggered and satisfied in TG6.
- Planning, business, and developer coverage now exist for this workflow.
- Impacted indexes are updated.
- No ADR was required for the final shipped shape.

## Permission checkpoint

No additional `/implement-next` step is pending for this guide.

If you want more work beyond this completed slice, please approve a separate follow-up such as:

- an explicit live Azure smoke validation
- a readiness/review pass
- a new implementation-guide update if requirements have changed

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

### 2026-04-24 — TG6 verification, docs, and closeout slice

- Reviewed the implementation guide, current handoff, the local `implementation-slice-guard` instructions, and the docs-update / pytest-TDD gates to confirm TG6 was the next eligible full slice.
- Selected the full TG6 slice because the remaining work was one cohesive closeout increment: verification, docs/index sync, and any regressions uncovered by the broadened suite.
- Ran the focused then full pytest progression and found three closeout issues that needed fixing before the workflow could be called complete:
  - shared-module boundary violation from `upload_run.py` importing helper functions from `run.py`
  - end-to-end stdin imports dropping `stdin_text` from the graph state contract
  - missing enforcement for the documented `--allow-external-path` policy
- Added focused regression tests first for lazy package re-export, stdin end-to-end flow, and external-path rejection, then fixed the implementation.
- Extracted shared managed-runtime setup/cleanup into `ComicBook/comicbook/runtime_deps.py`, updated `run.py` and `upload_run.py` to use it, and changed `comicbook.__init__` to a lazy `upload_templates` export.
- Added `stdin_text` to `ImportRunState` so stdin-driven imports survive graph execution.
- Implemented path-policy enforcement in `upload_load_file.py` and updated upload graph/CLI tests to opt into external paths where appropriate.
- Added `docs/business/template-upload-workflow/index.md` and `docs/developer/template-upload-workflow/index.md`, then synced `docs/index.md`, `docs/business/index.md`, and `docs/developer/index.md`.
- Verified the final closeout evidence:
  - `uv run python -m pytest -q tests/test_upload_load_file.py tests/test_upload_run_cli.py tests/test_upload_graph.py` → **19 passed**
  - `uv run python -m pytest -q` → **114 passed**
  - documented CLI sample commands both succeeded with temporary local env values

*End of handoff.*
