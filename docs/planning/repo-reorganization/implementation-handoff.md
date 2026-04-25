# Implementation Handoff: Repository Reorganization

- Status: TG1 completed, TG2 pending, TG3 pending, TG4 pending, TG5 pending
- Last updated: 2026-04-25
- Implementation guide: `docs/planning/repo-reorganization/implementation.md`
- Planning index: `docs/planning/repo-reorganization/index.md`
- Business doc: `docs/business/repo-reorganization/index.md`
- Developer doc: `docs/developer/repo-reorganization/index.md`
- ADR: `docs/planning/adr/ADR-0002-repo-reorganization.md`

## Current status summary

The repository has now completed TG1 from the reorganization implementation guide.

What is true after this session:

- `workflows/pipelines/shared/logging.py` is the tested shared logging foundation for the target tree
- focused shared logging tests now exist under `workflows/tests/shared/test_logging.py`
- the logging formatter now promotes standard optional fields and flattens `error.code`, `error.message`, and `error.retryable` when callers pass an `error` mapping
- default JSON output and opt-in text output are both covered by tests
- ADR-0002 has moved from **Proposed** to **Accepted** as required when TG1 lands
- planning, business, and developer docs now all include repository-reorganization material

What is still true after this session:

- the live runtime still resides under `ComicBook/comicbook/`
- the live tests still reside primarily under `ComicBook/tests/`
- `workflows/` is not yet the active packaged project root
- no legacy runtime module imports `pipelines.shared.logging` yet
- compatibility wrappers do not exist yet

## TaskGroup status table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Finalize and verify the shared logging foundation | completed | Shared logging module aligned with the standard, covered by focused pytest scope, and documented across the triad. |
| TG2 | Move package and tests into `workflows/` with compatibility wrappers | pending | Next eligible TaskGroup. Start with a small bootstrap slice rather than the full TaskGroup. |
| TG3 | Split shared and workflow-specific state modules | pending | Blocked on TG2 completing the package move. |
| TG4 | Complete structured logging adoption and template-upload naming cleanup | pending | Blocked on TG3. |
| TG5 | Remove compatibility layer, promote reused modules, and close out docs | pending | Blocked on TG4. |

## Last completed slice

### Selected TaskGroup and slice

- **TaskGroup:** TG1
- **Slice:** complete TG1 — finalize and verify the shared logging foundation

### Why this slice size was chosen

Using the local `implementation-slice-guard` guidance, TG1 was the first unfinished TaskGroup with no dependencies, and all remaining TG1 work was tightly related to one shared module plus one focused test file. That made the full TaskGroup small enough to fit one coherent, reviewable commit-sized slice without crossing into unrelated migration concerns.

### Completed work from this session

1. Reviewed `workflows/pipelines/shared/logging.py` against `docs/standards/logging-standards.md`.
2. Updated the formatter so required fields stay stable, promoted optional fields remain top-level, and non-promoted fields stay nested under `extra`.
3. Added support for flattening an `error` mapping into `error.code`, `error.message`, and `error.retryable` output fields.
4. Kept exception serialization, JSON-default behavior, and opt-in text formatting intact.
5. Added focused pytest coverage under `workflows/tests/shared/test_logging.py` for formatter behavior, helper behavior, and duplicate-handler protection.
6. Confirmed legacy runtime modules still do **not** import the target shared logger.
7. Updated the documentation triad and ADR status for the now-started migration.

## Files changed in this session

- `workflows/pipelines/shared/logging.py`
- `workflows/tests/shared/test_logging.py`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`
- `docs/planning/adr/ADR-0002-repo-reorganization.md`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/index.md`
- `docs/business/index.md`
- `docs/developer/index.md`

## Tests run and results

Primary verification command run from the repository root:

```bash
PYTHONPATH=workflows uv run --project "ComicBook" --no-sync pytest -q workflows/tests/shared/test_logging.py
```

Result:

- `5 passed in 0.01s`

Additional verification performed:

- confirmed by search that no file under `ComicBook/comicbook/` imports `pipelines.shared.logging`

## Documentation updated

### Planning

- updated `docs/planning/repo-reorganization/index.md`
- updated this handoff file
- updated `docs/planning/adr/ADR-0002-repo-reorganization.md` from **Proposed** to **Accepted**

### Business

- added `docs/business/repo-reorganization/index.md`
- updated `docs/business/index.md`

### Developer

- added `docs/developer/repo-reorganization/index.md`
- updated `docs/developer/index.md`

### Cross-section indexes

- updated `docs/index.md`

## Blockers or open questions

- No blocker remains for TG1.
- Direct `python` / `pytest` executables were not available in the shell environment, so verification used the existing locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- Running Python verification created untracked `__pycache__` directories under `workflows/pipelines/`; they were left in place because delete operations are approval-gated in this workflow.

## Exact next recommended slice

### TG2 bootstrap slice: make `workflows/` the active Python project root

Recommended next implementation slice:

1. create `workflows/pyproject.toml` from the current `ComicBook/pyproject.toml`
2. move `ComicBook/.env.example` to `workflows/.env.example`
3. update package discovery and pytest configuration so the project is intended to run from `workflows/`
4. keep the slice bounded: do **not** move runtime modules, tests, or compatibility wrappers yet

Why this next slice is recommended:

- it is the smallest TG2 increment that creates real migration progress
- it unlocks later module moves without forcing a huge multi-concern commit
- it does not require package installation, copy operations, or delete operations if handled with edits and moves only

Boundaries for the next session:

- do not start TG3+
- do not remove legacy paths yet
- do not add wrapper logic until the new project root metadata exists

## Session log

### 2026-04-24 — Planning session

- Created `docs/planning/repo-reorganization/implementation.md` as the primary implementation document.
- Created the initial `docs/planning/repo-reorganization/implementation-handoff.md` handoff ledger.
- Updated planning indexes for the new implementation material.
- No runtime code changed in that session.

### 2026-04-25 — TG1 implementation session

- Reviewed the implementation guide, current handoff, `workflows/pipelines/shared/logging.py`, the logging standard, and the local `implementation-slice-guard` instructions to choose the next eligible slice.
- Loaded and applied `pytest-tdd-guard` because the slice changed Python behavior in the shared logging module.
- Loaded and applied `docs-update-guard` because the slice materially changed observability infrastructure and developer-facing migration status.
- Completed TG1 as one cohesive slice.
- Added focused logging tests and ran the TG1 pytest scope successfully.
- Updated the planning, business, and developer docs plus ADR-0002 to reflect that implementation has started and TG1 is complete.

## Permission checkpoint

Stop here.

Do **not** start TG2 or any other follow-up work until the user explicitly approves another run such as:

`/implement-next docs/planning/repo-reorganization/implementation.md docs/planning/repo-reorganization/implementation-handoff.md`
