# Implementation Handoff: Template Upload Workflow

- Status: TG1 complete, TG2 pending
- Last updated: 2026-04-24
- Implementation guide: `docs/planning/template-upload-workflow/implementation.md`
- Planning index: `docs/planning/template-upload-workflow/index.md`

## Current status summary

This handoff tracks the standalone implementation guide for the template-upload workflow.

Current repository state:

- planning exists at `docs/planning/template-upload-workflow/plan.md`
- canonical sample input exists at `docs/planning/template-upload-workflow/sample_input.json`
- there is no `ComicBook/comicbook/upload_run.py`
- there is no `ComicBook/comicbook/upload_graph.py`
- there are no `nodes/upload_*.py` modules
- upload-specific contract tests now exist under `ComicBook/tests/`
- there are no workflow-specific business or developer docs yet for this workflow

In short: the workflow contract is now locked in tests, but the upload runtime is still not implemented.

## TaskGroup status table

| TaskGroup | Title | Status | Notes |
|---|---|---|---|
| TG1 | Lock the contract with focused failing tests | completed | Added upload contract tests and verified they fail on missing upload modules plus missing import DB contracts. |
| TG2 | Add shared persistence, config, and state scaffolding | pending | `db.py`, `config.py`, and `state.py` still do not contain import-workflow contracts. |
| TG3 | Implement file ingest, validation, and resumability | pending | No upload ingest/validation/resume nodes exist yet. |
| TG4 | Implement backfill, write-mode routing, and persistence | pending | No metadata prompt module, decision node, or upload persist node exists yet. |
| TG5 | Wire the graph, CLI, package export, and reporting | pending | No upload runtime entry point or graph currently exists. |
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

These are not blockers for starting TG2, but they should be watched during implementation:

- The final code may show that `router_llm.py` needs a tiny shared helper for generic schema calls. If so, keep that change additive and do not disturb the image-router contract.
- Fingerprint-drift reporting depends on the exact prompt-table lookup shape in `db.py`; verify it with tests before finalizing report language.
- If the live Azure smoke test reveals transport behavior not captured by current mocks, update the implementation guide or developer docs during TG6.
- If the implementation materially changes concurrency or persistence beyond this guide, add an ADR before calling the work complete.

## Exact next recommended slice

- Start **TG2** from `docs/planning/template-upload-workflow/implementation.md`.
- First concrete actions:
  1. extend `ComicBook/comicbook/state.py` with import-specific status literals and TypedDicts
  2. extend `ComicBook/comicbook/config.py` with upload guardrail settings and validation
  3. extend `ComicBook/comicbook/db.py` with `import_runs`, `import_row_results`, import-lock helpers, and the new DAO methods expected by the tests
- Do **not** start by wiring the CLI or graph yet. The next slice should make the new shared contracts pass before node modules are added.

## Suggested verification path for the next implementation slice

When TG2 is in progress, keep the verification scope narrow and contract-focused:

```bash
uv run python -m pytest -q tests/test_db.py tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_upload_persist.py tests/test_upload_run_cli.py
```

Run it from `ComicBook/`. The current expected failure set is limited to missing upload modules and missing import shared contracts. As TG2 lands, DB/config/state-related failures should be reduced before node and CLI failures.

## Documentation gate note

- The full docs triad is still **not** required yet for this slice because only test contracts and planning handoff state changed; no upload runtime behavior shipped.
- Once runtime behavior starts landing in shared modules or workflow code, this workflow will require business and developer docs plus index maintenance before it can be marked complete.

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

*End of handoff.*
