# Implementation Handoff: Repository Reorganization

- Status: TG1 completed, TG2 in progress, TG3 pending, TG4 pending, TG5 pending
- Last updated: 2026-04-25
- Implementation guide: `docs/planning/repo-reorganization/implementation.md`
- Planning index: `docs/planning/repo-reorganization/index.md`
- Business doc: `docs/business/repo-reorganization/index.md`
- Developer doc: `docs/developer/repo-reorganization/index.md`
- ADR: `docs/planning/adr/ADR-0002-repo-reorganization.md`

## Current status summary

The repository has now completed TG1 plus seven TG2 slices: the project-root bootstrap, the shared config/deps move, the shared repo-protection move, the shared fingerprint move, the shared database move, the shared execution-helper move, and the shared runtime-deps move.

What is true after this session:

- `workflows/pipelines/shared/logging.py` is the tested shared logging foundation for the target tree
- focused shared logging tests now exist under `workflows/tests/shared/test_logging.py`
- `workflows/pyproject.toml` now exists and defines target-tree package discovery plus pytest configuration for running focused scopes from `workflows/`
- `workflows/.env.example` is now the shared environment-template path for the migration
- `workflows/pipelines/shared/config.py` and `workflows/pipelines/shared/deps.py` are now the source of truth for the shared configuration and dependency-container modules
- `workflows/pipelines/shared/repo_protection.py` is now the source of truth for repo-protection checks and CLI helpers
- `workflows/pipelines/shared/fingerprint.py` is now the source of truth for deterministic prompt fingerprinting and prompt materialization helpers
- `workflows/pipelines/shared/db.py` is now the source of truth for the shared SQLite DAO, persistence records, and run-lock helpers
- `workflows/pipelines/shared/execution.py` is now the source of truth for shared graph-execution helpers such as `bind_node`, `prepare_initial_state`, and `run_graph_with_lock`
- `workflows/pipelines/shared/runtime_deps.py` is now the source of truth for managed runtime dependency construction and cleanup
- `workflows/comicbook/config.py` and `workflows/comicbook/deps.py` are the first explicit target-tree compatibility wrappers for legacy imports
- `workflows/comicbook/repo_protection.py` now provides the matching target-tree compatibility wrapper for the repo-protection surface
- `workflows/comicbook/fingerprint.py` now provides the matching target-tree compatibility wrapper for the fingerprint helper surface
- `workflows/comicbook/db.py` now provides the matching target-tree compatibility wrapper for the database surface
- `workflows/comicbook/execution.py` now provides the matching target-tree compatibility wrapper for the execution-helper surface
- `workflows/comicbook/runtime_deps.py` now provides the matching target-tree compatibility wrapper for the runtime-deps surface
- `workflows/comicbook/__init__.py` now preserves the legacy package-root `upload_templates` convenience export while TG2 compatibility wrappers accumulate
- `ComicBook/comicbook/config.py` and `ComicBook/comicbook/deps.py` now act as thin legacy wrappers so the old package root can still resolve the migrated shared modules during TG2
- `ComicBook/comicbook/repo_protection.py` now acts as a thin legacy wrapper so the old package root and `ComicBook/scripts/check_do_not_change.py` still resolve the moved implementation during TG2
- `ComicBook/comicbook/fingerprint.py` now acts as a thin legacy wrapper so the old package root still resolves the moved fingerprint helpers during TG2
- `ComicBook/comicbook/db.py` now acts as a thin legacy wrapper so the old package root still resolves the moved DAO and persistence dataclasses during TG2
- `ComicBook/comicbook/execution.py` now acts as a thin legacy wrapper so the old package root still resolves the moved execution helpers during TG2
- `ComicBook/comicbook/runtime_deps.py` now acts as a thin legacy wrapper so the old package root still resolves the moved runtime-dependency helpers during TG2
- setup-facing READMEs and repository-reorganization docs now point at the new target-tree project root, env-template path, and current TG2 module-move progress
- focused target-tree repo-protection tests now exist under `workflows/tests/shared/test_repo_protection.py`
- focused target-tree fingerprint tests now exist under `workflows/tests/shared/test_fingerprint.py`
- focused target-tree database tests now exist under `workflows/tests/shared/test_db.py`
- focused target-tree execution tests now exist under `workflows/tests/shared/test_execution.py`
- focused target-tree runtime-deps tests now exist under `workflows/tests/shared/test_runtime_deps.py`

What is still true after this session:

- the live runtime still resides under `ComicBook/comicbook/`
- the live tests still reside primarily under `ComicBook/tests/`
- most of the runtime module move into `workflows/pipelines/` has not happened yet
- the live workflow entry points and most workflow-owned modules still reside under `ComicBook/comicbook/`
- CLI entry points still do not emit fully structured `log_event(...)` records directly; that adoption work is still pending later in TG2
- compatibility wrappers exist only for `config`, `deps`, `repo_protection`, `fingerprint`, `db`, `execution`, and `runtime_deps`, plus the package-root `upload_templates` re-export; graph, node, state, and most other legacy imports still do not have target-tree wrappers yet
- default pricing lookup in `workflows/pipelines/shared/runtime_deps.py` still falls back to `ComicBook/comicbook/pricing.json` until the workflow asset move lands later in TG2

## TaskGroup status table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Finalize and verify the shared logging foundation | completed | Shared logging module aligned with the standard, covered by focused pytest scope, and documented across the triad. |
| TG2 | Move package and tests into `workflows/` with compatibility wrappers | in progress | Bootstrap plus seven shared-module slices are complete: target-tree project metadata landed, `config.py`/`deps.py`/`repo_protection.py`/`fingerprint.py`/`db.py`/`execution.py`/`runtime_deps.py` now live in `pipelines.shared`, and matching `workflows/comicbook/` wrappers exist. Most TG2 work is still pending. |
| TG3 | Split shared and workflow-specific state modules | pending | Blocked on TG2 completing the package move. |
| TG4 | Complete structured logging adoption and template-upload naming cleanup | pending | Blocked on TG3. |
| TG5 | Remove compatibility layer, promote reused modules, and close out docs | pending | Blocked on TG4. |

## Last completed slice

### Selected TaskGroup and slice

- **TaskGroup:** TG2
- **Slice:** TG2 runtime-deps move — migrate the managed runtime-construction helper with thin compatibility wrappers and focused runtime-entrypoint tests

### Why this slice size was chosen

The first unfinished TaskGroup remained TG2, but the remaining work still spans several unrelated shared modules plus both workflows. The local `implementation-slice-guard` skill was present in the repository at `.opencode/skills/implementation-slice-guard/SKILL.md` but was not exposed through the skill tool, so its selection rules were applied manually from that file. Following that guidance, this slice was chosen because `runtime_deps.py` is one cohesive shared runtime-construction helper with a focused test surface around pricing resolution, managed dependency construction, dependency reuse, and cleanup. That keeps the session commit-sized while advancing the dependency chain toward later CLI/run-module migration without mixing in full workflow graph/run moves.

### Completed work from this session

1. Added `workflows/pipelines/shared/runtime_deps.py` as the new source-of-truth home for pricing loading, managed runtime dependency construction, dependency reuse, and runtime resource cleanup.
2. Switched the moved helper to build managed dependencies with `get_logger(__name__)` from the shared logging module instead of the legacy `logging.getLogger("comicbook.run")` call.
3. Added `workflows/comicbook/runtime_deps.py` as the target-tree compatibility wrapper for legacy `comicbook.runtime_deps` imports.
4. Converted `ComicBook/comicbook/runtime_deps.py` into a thin legacy wrapper so the old package root still resolves the moved implementation during TG2.
5. Kept default pricing resolution working without moving workflow assets yet by falling back to `ComicBook/comicbook/pricing.json` when the target-tree pricing file is not present.
6. Updated `workflows/comicbook/__init__.py` so the target-tree compatibility package preserves the legacy package-root `upload_templates` convenience export while dedicated run-module wrappers are still pending.
7. Added focused target-tree coverage in `workflows/tests/shared/test_runtime_deps.py` for wrapper identity, pricing loading, managed dependency construction, dependency reuse, cleanup behavior, and the package-root `upload_templates` re-export.
8. Verified the focused runtime-deps scope, the broader target-tree shared regression scope, and representative legacy runtime-entrypoint regression scopes successfully, then reconciled the handoff so it matches the repository state for this completed slice.

## Files changed in this session

- `workflows/pipelines/shared/runtime_deps.py`
- `workflows/comicbook/runtime_deps.py`
- `workflows/comicbook/__init__.py`
- `workflows/tests/shared/test_runtime_deps.py`
- `ComicBook/comicbook/runtime_deps.py`
- `workflows/README.md`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`

## Tests run and results

Focused target-tree verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_runtime_deps.py
```

Result:

- `8 passed in 0.30s`

Broader target-tree shared regression command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_logging.py tests/shared/test_config_and_deps.py tests/shared/test_repo_protection.py tests/shared/test_fingerprint.py tests/shared/test_db.py tests/shared/test_execution.py tests/shared/test_runtime_deps.py
```

Result:

- `44 passed in 1.55s`

Legacy runtime-entrypoint regression command run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_budget_guard.py tests/test_input_file_support.py tests/test_upload_run_cli.py
```

Result:

- `31 passed in 1.07s`

Target-tree compatibility import check run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync python - <<'PY'
from comicbook import upload_templates as exported
from comicbook.upload_run import upload_templates as direct
print(exported is direct)
PY
```

Result:

- printed `True`

Additional verification performed:

- strict red/green sequencing was adapted in this run because the repository already contained an in-progress runtime-deps draft when this session began; the smallest meaningful focused pytest scope was still run first to validate and finish that slice before broader verification
- confirmed target-tree compatibility imports resolve through `workflows/comicbook/runtime_deps.py`
- confirmed managed dependency construction now uses the shared logger factory while preserving the same directory-creation and resource-management behavior
- confirmed default pricing lookup still works before the pricing asset moves by falling back to `ComicBook/comicbook/pricing.json`
- confirmed the target-tree compatibility package still re-exports `upload_templates` from the package root
- confirmed representative legacy runtime-entrypoint tests still pass after the wrapper conversion

## Documentation updated

### Planning

- updated `docs/planning/repo-reorganization/index.md`
- updated this handoff file

### Business

- updated `docs/business/repo-reorganization/index.md`

### Developer

- updated `docs/developer/repo-reorganization/index.md`

### README / setup docs

- updated `workflows/README.md`

### ADR

- no ADR update was needed in this slice because moving `runtime_deps.py` followed the already accepted migration plan and did not introduce a new architecture decision

## Blockers or open questions

- No code blocker remains for this slice.
- The local `implementation-slice-guard` skill exists in the repository but is not currently loadable through the skill tool, so slice selection used the checked-in skill file directly.
- Direct `pytest` is still unavailable in the shell environment, so verification reused the existing locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- The handoff document had fallen behind the actual repository state before this session because the runtime-deps slice files already existed in the working tree; this update reconciles the handoff with the implemented slice and current verification evidence.
- The legacy `ComicBook/comicbook/config.py`, `deps.py`, `repo_protection.py`, `fingerprint.py`, `db.py`, `execution.py`, and `runtime_deps.py` wrappers currently add the sibling `workflows/` directory to `sys.path` so the old package root can keep working while TG2 is incomplete. This is a temporary bridge, not the long-term compatibility mechanism.
- `workflows/pipelines/shared/fingerprint.py` intentionally falls back to loading the legacy `ComicBook/comicbook/state.py` module for `RenderedPrompt` when the target-tree `comicbook.state` wrapper does not exist yet. This is a temporary TG2 bridge that should disappear once TG3 moves state ownership.
- `workflows/pipelines/shared/db.py` intentionally falls back to loading the legacy `ComicBook/comicbook/state.py` module for `TemplateSummary` when the target-tree state wrapper does not exist yet. This is a temporary TG2 bridge that should disappear once TG3 moves state ownership.
- `workflows/pipelines/shared/execution.py` intentionally falls back to loading the legacy `ComicBook/comicbook/state.py` and `ComicBook/comicbook/nodes/ingest.py` modules when target-tree wrappers do not exist yet. This is a temporary TG2 bridge that should disappear once later TG2/TG3 work moves those dependencies cleanly.
- `workflows/pipelines/shared/runtime_deps.py` intentionally falls back to `ComicBook/comicbook/pricing.json` when the target-tree pricing asset is not present yet. This is a temporary TG2 bridge that should disappear once the workflow pricing file moves.
- The `workflows/comicbook/__init__.py` package-root `upload_templates` re-export currently resolves through the legacy `ComicBook/comicbook/upload_run.py` module until the dedicated run/upload_run slice lands.
- Running Python verification touched tracked and untracked `__pycache__` artifacts under `workflows/`; they were left in place because delete/revert cleanup is approval-gated in this workflow.

## Exact next recommended slice

### TG2 next slice: move the workflow CLI entry points with structured `log_event(...)` adoption

Recommended next implementation slice:

1. move `ComicBook/comicbook/run.py` into `workflows/pipelines/workflows/image_prompt_gen/run.py` and `ComicBook/comicbook/upload_run.py` into `workflows/pipelines/workflows/template_upload/run.py`
2. add `workflows/comicbook/run.py` and `workflows/comicbook/upload_run.py` plus any required legacy-wrapper updates so both `pipelines.*` and temporary `comicbook.*` imports continue to resolve
3. adopt `log_event(...)` in those CLI and non-node runtime entry points while preserving current command behavior and argument parsing
4. add focused target-tree tests that prove both entry points still work from the new root, including the package-root `upload_templates` convenience export, while keeping the slice bounded away from graph/node moves and TG3 state splitting

Why this next slice is recommended:

- it is the next foundational TG2 cluster after `runtime_deps.py` because the entry points now depend on the moved shared helpers and still own the remaining non-node logging adoption called out in the implementation guide
- `run.py` and `upload_run.py` are tightly related as the two CLI/runtime entry points, and they share one focused test strategy around argument parsing, dependency resolution, and log-event emission
- leaving graph assembly, workflow nodes, and TG3 state splitting for later keeps the next commit narrowly focused on entrypoint ownership and observability contracts

Boundaries for the next session:

- do not start TG3+
- do not move workflow graphs or nodes in the same slice as the CLI entry points
- do not remove legacy paths yet
- do not split `state.py` until TG3

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

### 2026-04-25 — TG2 bootstrap implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice.
- Loaded and applied `docs-update-guard` because this slice changed developer setup expectations and setup-facing documentation.
- Added `workflows/pyproject.toml` and configured target-tree package discovery plus pytest settings for `workflows/`.
- Moved `ComicBook/.env.example` to `workflows/.env.example`.
- Updated setup-facing READMEs plus planning, business, and developer docs to reflect the new target-tree project-root metadata and environment-template path.
- The first verification run exposed that `pipelines` was not importable during pytest collection from `workflows/`; the slice fixed that by adding `pythonpath = ["."]` to `workflows/pyproject.toml`.
- Re-ran the focused target-tree pytest scope successfully from `workflows/`.

### 2026-04-25 — TG2 shared config/deps implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice after the bootstrap work.
- Loaded and applied `pytest-tdd-guard` because moving shared modules and adding compatibility wrappers is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed import/location contracts and maintainer-facing migration status.
- Added a focused target-tree test first; the initial run failed because `pipelines.shared.config` and `pipelines.shared.deps` did not exist yet.
- Added `workflows/pipelines/shared/config.py` and `workflows/pipelines/shared/deps.py` as the new source-of-truth homes for the shared configuration and dependency-container modules.
- Added the first target-tree `workflows/comicbook/` wrappers for `config` and `deps`.
- Converted the legacy `ComicBook/comicbook/config.py` and `deps.py` modules into thin wrappers so the old package root can still resolve the migrated shared modules during TG2.
- Added focused target-tree tests for the shared modules and wrapper identity, then re-ran both target-tree and legacy regression scopes successfully.
- Updated planning, business, developer, and setup docs to reflect that TG2 has started the real shared-module move.

### 2026-04-25 — TG2 repo-protection implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice after the config/deps work.
- Loaded and applied `pytest-tdd-guard` because moving `repo_protection.py` behind wrapper layers is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed a path-sensitive helper contract and maintainer-facing migration status.
- Added a focused target-tree test first; the initial run failed because `pipelines.shared.repo_protection` did not exist yet.
- Added `workflows/pipelines/shared/repo_protection.py` as the new source-of-truth home for repo-protection helpers.
- Added the matching `workflows/comicbook/repo_protection.py` target-tree compatibility wrapper and converted the legacy `ComicBook/comicbook/repo_protection.py` module into a thin wrapper.
- Verified the migrated helper through focused target-tree tests, the legacy CLI script path, and the legacy repo-protection regression scope.
- Updated planning, business, developer, and setup docs to reflect that TG2 now includes a moved path-sensitive helper while the protected asset itself still remains under `ComicBook/DoNotChange`.

### 2026-04-25 — TG2 fingerprint implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice after the repo-protection work.
- Loaded and applied `pytest-tdd-guard` because moving `fingerprint.py` behind wrapper layers is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed shared-module ownership and maintainer-facing migration status.
- Added a focused target-tree test first; the initial run failed because `pipelines.shared.fingerprint` did not exist yet.
- Added `workflows/pipelines/shared/fingerprint.py` as the new source-of-truth home for prompt fingerprinting and prompt materialization helpers.
- Added the matching `workflows/comicbook/fingerprint.py` target-tree compatibility wrapper and converted the legacy `ComicBook/comicbook/fingerprint.py` module into a thin wrapper.
- Kept the moved helper importable from the target tree by adding a temporary fallback to the legacy `RenderedPrompt` model until TG3 moves state ownership.
- Verified the migrated helper through focused target-tree tests and the legacy fingerprint regression scope, then re-ran the broader shared-module regression scopes successfully.
- Updated planning, business, developer, and setup docs to reflect that TG2 now includes a moved fingerprint helper while state ownership still remains deferred.

### 2026-04-25 — TG2 database implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice after the fingerprint work.
- Loaded and applied `pytest-tdd-guard` because moving `db.py` behind wrapper layers is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed shared-module ownership, persistence-helper import contracts, and maintainer-facing migration status.
- Added a focused target-tree test first; the initial run failed because `pipelines.shared.db` did not exist yet.
- Added `workflows/pipelines/shared/db.py` as the new source-of-truth home for the shared SQLite DAO, persistence dataclasses, and run-lock helpers.
- Added the matching `workflows/comicbook/db.py` target-tree compatibility wrapper and converted the legacy `ComicBook/comicbook/db.py` module into a thin wrapper.
- Kept the moved helper importable from the target tree by adding a temporary fallback to the legacy `TemplateSummary` model until TG3 moves state ownership.
- Verified the migrated helper through focused target-tree tests, a broader target-tree shared regression scope, and representative legacy image-workflow and template-upload smoke tests.
- Updated planning, business, developer, and setup docs to reflect that TG2 now includes a moved database helper while state ownership and runtime logging adoption still remain deferred.

### 2026-04-25 — TG2 execution implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice after the database work.
- Loaded and applied `pytest-tdd-guard` because moving `execution.py` behind wrapper layers is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed shared-module ownership, orchestration-helper import contracts, and maintainer-facing migration status.
- Added a focused target-tree test first; the initial run failed because `pipelines.shared.execution` did not exist yet.
- Added `workflows/pipelines/shared/execution.py` as the new source-of-truth home for shared graph-execution helpers.
- Added the matching `workflows/comicbook/execution.py` target-tree compatibility wrapper and converted the legacy `ComicBook/comicbook/execution.py` module into a thin wrapper.
- Kept the moved helper importable from the target tree by adding temporary fallbacks to the legacy ingest/state modules until later TG2 and TG3 work moves those dependencies cleanly.
- Verified the migrated helper through focused target-tree tests, a broader target-tree shared regression scope, and representative legacy image-workflow, template-upload, and example-workflow smoke tests.
- Updated planning, business, developer, and setup docs to reflect that TG2 now includes moved execution helpers while runtime construction, state ownership, and runtime logging adoption still remain deferred.

### 2026-04-25 — TG2 runtime-deps implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice after the execution work.
- Loaded and applied `pytest-tdd-guard` because moving `runtime_deps.py` behind wrapper layers and changing logger construction is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed shared-module ownership, runtime-construction behavior, and maintainer-facing migration status.
- Adapted strict red/green sequencing because the repository already contained an in-progress runtime-deps draft when this session began; instead, the focused target-tree pytest scope was run first to validate and finish the existing slice cleanly.
- Added `workflows/pipelines/shared/runtime_deps.py` as the new source-of-truth home for pricing loading, managed dependency construction, dependency reuse, and runtime resource cleanup.
- Added the matching `workflows/comicbook/runtime_deps.py` target-tree compatibility wrapper and converted `ComicBook/comicbook/runtime_deps.py` into a thin legacy wrapper.
- Switched managed dependency construction to `get_logger(__name__)`, kept default pricing resolution working through a temporary fallback to the legacy pricing asset, and kept the package-root `upload_templates` convenience export available from `workflows/comicbook/__init__.py`.
- Expanded focused target-tree coverage in `workflows/tests/shared/test_runtime_deps.py`, including the package-root `upload_templates` re-export.
- Verified the runtime-deps slice through focused target-tree tests, the broader target-tree shared regression scope, a direct import check for the compatibility package export, and representative legacy runtime-entrypoint regression scopes.
- Reconciled this handoff with the repository state so the recorded completed slice now matches the implemented files and verification evidence.

## Permission checkpoint

Stop here.

Do **not** start the next TG2 slice or any other follow-up work until the user explicitly approves another run such as:

`/implement-next docs/planning/repo-reorganization/implementation.md docs/planning/repo-reorganization/implementation-handoff.md`
