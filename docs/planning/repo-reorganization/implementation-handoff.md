# Implementation Handoff: Repository Reorganization

- Status: TG1 completed, TG2 in progress, TG3 pending, TG4 pending, TG5 pending
- Last updated: 2026-04-25
- Implementation guide: `docs/planning/repo-reorganization/implementation.md`
- Planning index: `docs/planning/repo-reorganization/index.md`
- Business doc: `docs/business/repo-reorganization/index.md`
- Developer doc: `docs/developer/repo-reorganization/index.md`
- ADR: `docs/planning/adr/ADR-0002-repo-reorganization.md`

## Current status summary

The repository has now completed TG1 plus nine TG2 slices: the project-root bootstrap, the shared config/deps move, the shared repo-protection move, the shared fingerprint move, the shared database move, the shared execution-helper move, the shared runtime-deps move, the workflow CLI entry-point move, and the workflow graph move.

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
- `workflows/pipelines/workflows/image_prompt_gen/run.py` is now the source of truth for the image workflow CLI and library entry point
- `workflows/pipelines/workflows/template_upload/run.py` is now the source of truth for the template-upload CLI and library entry point
- `workflows/pipelines/workflows/image_prompt_gen/graph.py` is now the source of truth for the image workflow graph assembly and `runtime_gate` logic
- `workflows/pipelines/workflows/template_upload/graph.py` is now the source of truth for the template-upload workflow graph assembly
- the moved entry points now emit structured `log_event(...)` records directly for batch progress, single-run lifecycle, import-run lifecycle, and CLI error handling
- the moved entry points now call the moved target-tree graph modules directly instead of routing back through the legacy graph modules
- `workflows/comicbook/config.py` and `workflows/comicbook/deps.py` are the first explicit target-tree compatibility wrappers for legacy imports
- `workflows/comicbook/repo_protection.py` now provides the matching target-tree compatibility wrapper for the repo-protection surface
- `workflows/comicbook/fingerprint.py` now provides the matching target-tree compatibility wrapper for the fingerprint helper surface
- `workflows/comicbook/db.py` now provides the matching target-tree compatibility wrapper for the database surface
- `workflows/comicbook/execution.py` now provides the matching target-tree compatibility wrapper for the execution-helper surface
- `workflows/comicbook/runtime_deps.py` now provides the matching target-tree compatibility wrapper for the runtime-deps surface
- `workflows/comicbook/input_file.py` now provides the minimum target-tree compatibility wrapper needed by the moved image entry point
- `workflows/comicbook/graph.py` and `workflows/comicbook/upload_graph.py` now act as target-tree compatibility aliases to the moved graph modules
- `workflows/comicbook/run.py` and `workflows/comicbook/upload_run.py` now act as target-tree compatibility aliases to the moved `pipelines` entry-point modules
- `workflows/comicbook/__init__.py` now preserves the legacy package-root `upload_templates` convenience export and extends the target-tree compatibility package path to the still-legacy `ComicBook/comicbook/` tree while TG2 compatibility wrappers accumulate
- `ComicBook/comicbook/config.py` and `ComicBook/comicbook/deps.py` now act as thin legacy wrappers so the old package root can still resolve the migrated shared modules during TG2
- `ComicBook/comicbook/repo_protection.py` now acts as a thin legacy wrapper so the old package root and `ComicBook/scripts/check_do_not_change.py` still resolve the moved implementation during TG2
- `ComicBook/comicbook/fingerprint.py` now acts as a thin legacy wrapper so the old package root still resolves the moved fingerprint helpers during TG2
- `ComicBook/comicbook/db.py` now acts as a thin legacy wrapper so the old package root still resolves the moved DAO and persistence dataclasses during TG2
- `ComicBook/comicbook/execution.py` now acts as a thin legacy wrapper so the old package root still resolves the moved execution helpers during TG2
- `ComicBook/comicbook/runtime_deps.py` now acts as a thin legacy wrapper so the old package root still resolves the moved runtime-dependency helpers during TG2
- `ComicBook/comicbook/graph.py` and `ComicBook/comicbook/upload_graph.py` now act as legacy compatibility aliases to the moved graph modules
- `ComicBook/comicbook/run.py` and `ComicBook/comicbook/upload_run.py` now act as legacy compatibility aliases to the moved entry-point modules
- the run-module wrappers now preserve monkeypatch behavior by aliasing importers to the moved module objects instead of only re-exporting symbols
- the graph-module wrappers now preserve monkeypatch behavior by aliasing importers to the moved module objects instead of only re-exporting symbols
- setup-facing READMEs and repository-reorganization docs now point at the new target-tree project root, env-template path, and current TG2 module-move progress
- focused target-tree repo-protection tests now exist under `workflows/tests/shared/test_repo_protection.py`
- focused target-tree fingerprint tests now exist under `workflows/tests/shared/test_fingerprint.py`
- focused target-tree database tests now exist under `workflows/tests/shared/test_db.py`
- focused target-tree execution tests now exist under `workflows/tests/shared/test_execution.py`
- focused target-tree runtime-deps tests now exist under `workflows/tests/shared/test_runtime_deps.py`
- focused target-tree graph-wrapper tests now exist under `workflows/tests/image_prompt_gen/test_graph.py` and `workflows/tests/template_upload/test_graph.py`
- focused target-tree entry-point tests now exist under `workflows/tests/image_prompt_gen/test_run.py` and `workflows/tests/template_upload/test_run.py`

What is still true after this session:

- the live tests still reside primarily under `ComicBook/tests/`
- most workflow-owned module moves into `workflows/pipelines/` have not happened yet
- nodes, prompts, adapters, pricing assets, and the mixed state contracts still reside under `ComicBook/comicbook/`
- the moved graph modules still depend on legacy workflow-module bridges for nodes, prompts, adapters, pricing assets, and state; full target-tree workflow execution is not complete yet
- compatibility wrappers exist only for `config`, `deps`, `repo_protection`, `fingerprint`, `db`, `execution`, `runtime_deps`, `input_file`, `run`, `upload_run`, `graph`, and `upload_graph`, plus the package-root `upload_templates` re-export and the compatibility-package path fallback; node, state, and most other legacy imports still do not have explicit target-tree wrappers yet
- default pricing lookup in `workflows/pipelines/shared/runtime_deps.py` still falls back to `ComicBook/comicbook/pricing.json` until the workflow asset move lands later in TG2

## TaskGroup status table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Finalize and verify the shared logging foundation | completed | Shared logging module aligned with the standard, covered by focused pytest scope, and documented across the triad. |
| TG2 | Move package and tests into `workflows/` with compatibility wrappers | in progress | Bootstrap plus nine TG2 slices are complete: target-tree project metadata landed, seven shared modules now live in `pipelines.shared`, both workflow CLI entry points now live under `pipelines.workflows.*.run`, and both workflow graph modules now live under `pipelines.workflows.*.graph` with compatibility aliases. Most workflow-owned module moves are still pending. |
| TG3 | Split shared and workflow-specific state modules | pending | Blocked on TG2 completing the package move. |
| TG4 | Complete structured logging adoption and template-upload naming cleanup | pending | Blocked on TG3. |
| TG5 | Remove compatibility layer, promote reused modules, and close out docs | pending | Blocked on TG4. |

## Last completed slice

### Selected TaskGroup and slice

- **TaskGroup:** TG2
- **Slice:** TG2 workflow-graph move — migrate `graph.py` and `upload_graph.py` into `pipelines.workflows.*.graph`, switch the moved entry points to call those modules directly, and preserve compatibility through graph-module aliases plus focused graph-wrapper tests

### Why this slice size was chosen

The first unfinished TaskGroup remained TG2, and the next natural dependency cluster after the moved entry points was the pair of workflow graph modules those entry points still depended on indirectly. The local `implementation-slice-guard` skill was present in the repository at `.opencode/skills/implementation-slice-guard/SKILL.md` but was not exposed through the skill tool, so its selection rules were applied manually from that file again. Following that guidance, this slice was chosen because `graph.py` and `upload_graph.py` are the next tightly related workflow-owned boundary below the already moved `run.py` / `upload_run.py` modules. Keeping the slice bounded to those graph modules plus the minimum compatibility scaffolding avoided mixing in node moves, workflow-helper moves, or TG3 state splitting.

### Completed work from this session

1. Added `workflows/pipelines/workflows/image_prompt_gen/graph.py` as the new source-of-truth home for the image workflow graph assembly, including `runtime_gate`.
2. Added `workflows/pipelines/workflows/template_upload/graph.py` as the new source-of-truth home for the template-upload workflow graph assembly.
3. Switched `pipelines.workflows.image_prompt_gen.run` and `pipelines.workflows.template_upload.run` to call the moved graph modules directly instead of routing through legacy `comicbook.graph` imports.
4. Added `workflows/comicbook/graph.py` and `workflows/comicbook/upload_graph.py` as target-tree compatibility aliases to the moved graph modules.
5. Extended `workflows/comicbook/__init__.py` so the target-tree compatibility package includes the still-legacy `ComicBook/comicbook/` path, which keeps unmoved workflow-local modules importable during TG2.
6. Converted `ComicBook/comicbook/graph.py` and `ComicBook/comicbook/upload_graph.py` into legacy compatibility aliases so the old package root now resolves the moved graph implementations.
7. Added focused target-tree coverage in `workflows/tests/image_prompt_gen/test_graph.py` and `workflows/tests/template_upload/test_graph.py` for graph-wrapper identity and direct run-module delegation to the moved graph modules.
8. Verified the focused target-tree graph scope, the broader target-tree workflow scope, representative legacy graph regression scopes, and direct compatibility alias identity checks successfully.

## Files changed in this session

- `workflows/pipelines/workflows/image_prompt_gen/graph.py`
- `workflows/pipelines/workflows/image_prompt_gen/run.py`
- `workflows/pipelines/workflows/template_upload/graph.py`
- `workflows/pipelines/workflows/template_upload/run.py`
- `workflows/comicbook/__init__.py`
- `workflows/comicbook/graph.py`
- `workflows/comicbook/upload_graph.py`
- `workflows/tests/image_prompt_gen/test_graph.py`
- `workflows/tests/template_upload/test_graph.py`
- `ComicBook/comicbook/graph.py`
- `ComicBook/comicbook/upload_graph.py`
- `workflows/README.md`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`

## Tests run and results

Focused target-tree graph verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen/test_graph.py tests/template_upload/test_graph.py
```

Result:

- `4 passed in 0.15s`

Broader target-tree workflow regression command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen/test_graph.py tests/image_prompt_gen/test_run.py tests/template_upload/test_graph.py tests/template_upload/test_run.py
```

Result:

- `10 passed in 0.16s`

Legacy graph regression command run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_graph_happy.py tests/test_budget_guard.py tests/test_upload_graph.py
```

Result:

- `9 passed in 1.31s`

Target-tree compatibility alias identity check run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync python - <<'PY'
from comicbook.graph import run_workflow as wrapped_image_run_workflow
from comicbook.upload_graph import run_upload_workflow as wrapped_upload_run_workflow
from pipelines.workflows.image_prompt_gen.graph import run_workflow as moved_image_run_workflow
from pipelines.workflows.template_upload.graph import run_upload_workflow as moved_upload_run_workflow
print(wrapped_image_run_workflow is moved_image_run_workflow)
print(wrapped_upload_run_workflow is moved_upload_run_workflow)
PY
```

Result:

- printed `True`
- printed `True`

Additional verification performed:

- strict TDD was followed for the new target-tree graph coverage: the initial focused pytest run failed because the target-tree workflow graph modules did not exist yet, then the smallest implementation needed for that scope was added
- confirmed the moved entry points now resolve the moved graph modules directly through `pipelines.workflows.*.graph`
- confirmed both target-tree and legacy graph compatibility aliases resolve to the same moved module objects
- confirmed representative legacy graph tests still pass after the graph move and wrapper changes

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

- no ADR update was needed in this slice because moving the two workflow graph modules followed the already accepted migration plan and did not introduce a new architecture decision beyond that plan

## Blockers or open questions

- No code blocker remains for this slice.
- The local `implementation-slice-guard` skill exists in the repository but is not currently loadable through the skill tool, so slice selection used the checked-in skill file directly.
- Direct `pytest` is still unavailable in the shell environment, so verification reused the existing locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- The legacy `ComicBook/comicbook/config.py`, `deps.py`, `repo_protection.py`, `fingerprint.py`, `db.py`, `execution.py`, and `runtime_deps.py` wrappers currently add the sibling `workflows/` directory to `sys.path` so the old package root can keep working while TG2 is incomplete. This is a temporary bridge, not the long-term compatibility mechanism.
- `workflows/pipelines/shared/fingerprint.py` intentionally falls back to loading the legacy `ComicBook/comicbook/state.py` module for `RenderedPrompt` when the target-tree `comicbook.state` wrapper does not exist yet. This is a temporary TG2 bridge that should disappear once TG3 moves state ownership.
- `workflows/pipelines/shared/db.py` intentionally falls back to loading the legacy `ComicBook/comicbook/state.py` module for `TemplateSummary` when the target-tree state wrapper does not exist yet. This is a temporary TG2 bridge that should disappear once TG3 moves state ownership.
- `workflows/pipelines/shared/execution.py` intentionally falls back to loading the legacy `ComicBook/comicbook/state.py` and `ComicBook/comicbook/nodes/ingest.py` modules when target-tree wrappers do not exist yet. This is a temporary TG2 bridge that should disappear once later TG2/TG3 work moves those dependencies cleanly.
- `workflows/pipelines/shared/runtime_deps.py` intentionally falls back to `ComicBook/comicbook/pricing.json` when the target-tree pricing asset is not present yet. This is a temporary TG2 bridge that should disappear once the workflow pricing file moves.
- the moved graph modules still call into legacy workflow-local modules for nodes, prompts, adapters, pricing assets, and state until later TG2 and TG3 slices move those dependencies cleanly.
- Running Python verification touched tracked and untracked `__pycache__` artifacts under `workflows/`; they were left in place because delete/revert cleanup is approval-gated in this workflow.

## Exact next recommended slice

### TG2 next slice: move the workflow-local helper modules that still sit below the moved graphs

Recommended next implementation slice:

1. move the remaining workflow-local helper modules that the moved graphs and still-legacy nodes depend on, most likely `ComicBook/comicbook/input_file.py`, `router_llm.py`, `router_prompts.py`, `metadata_prompts.py`, `image_client.py`, and `pricing.json`, into the appropriate `workflows/pipelines/workflows/image_prompt_gen/` locations
2. add the minimum target-tree compatibility wrappers needed for those moved helper modules so both the moved graph layer and the still-legacy node layer can import them cleanly from `workflows/`
3. keep node implementations and TG3 state splitting out of that slice
4. add focused target-tree tests that prove the moved graph layer can import those helper modules from the new root without adding new path hacks

Why this next slice is recommended:

- it is the next dependency cluster after the graph move because the moved graph modules still rely on legacy workflow-local helpers for prompts, adapters, image generation, pricing, and input parsing
- moving those helper modules will reduce the amount of fallback behavior inside the target-tree compatibility package without yet mixing in node moves or TG3 state splitting
- leaving nodes and the mixed state file untouched keeps the next commit narrowly focused and still TG2-scoped

Boundaries for the next session:

- do not start TG3+
- do not move workflow nodes in the same slice as the workflow-local helper modules unless a tiny inseparable bridge is required
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

### 2026-04-25 — TG2 CLI entry-point implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill guidance to choose the next eligible commit-sized slice after the shared-module work.
- Loaded and applied `pytest-tdd-guard` because moving the workflow entry points and changing compatibility-wrapper behavior is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed developer-facing import ownership and runtime observability expectations.
- Added focused target-tree tests first; the initial run failed because the target-tree workflow packages and moved run modules did not exist yet.
- Added `workflows/pipelines/workflows/image_prompt_gen/run.py` and `workflows/pipelines/workflows/template_upload/run.py` as the new source-of-truth entry points.
- Added target-tree compatibility aliases for `comicbook.run` and `comicbook.upload_run`, plus the minimum `comicbook.input_file` wrapper needed for the moved image entry point.
- Converted the legacy `ComicBook/comicbook/run.py` and `upload_run.py` modules into compatibility aliases to the moved source-of-truth modules.
- The first broader legacy regression run exposed that plain symbol re-exports broke monkeypatch-based tests; the slice corrected that by switching the run-module wrappers to module aliases.
- Verified the slice through focused target-tree tests, broader target-tree logging/runtime regression tests, representative legacy runtime-entrypoint tests, and direct alias identity checks.
- Updated the planning, business, and developer docs plus `workflows/README.md` to reflect the new entry-point ownership and direct `log_event(...)` adoption.

### 2026-04-25 — TG2 workflow-graph implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill guidance to choose the next eligible commit-sized slice after the entry-point move.
- Loaded and applied `pytest-tdd-guard` because moving the workflow graph modules and changing the compatibility-wrapper path behavior is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed developer-facing import ownership and target-tree execution behavior.
- Added focused target-tree tests first; the initial run failed because the target-tree workflow graph modules did not exist yet.
- Added `workflows/pipelines/workflows/image_prompt_gen/graph.py` and `workflows/pipelines/workflows/template_upload/graph.py` as the new source-of-truth graph modules.
- Added target-tree compatibility aliases for `comicbook.graph` and `comicbook.upload_graph`, and extended the target-tree compatibility package path so still-legacy workflow-local modules can keep resolving during TG2.
- Converted the legacy `ComicBook/comicbook/graph.py` and `ComicBook/comicbook/upload_graph.py` modules into compatibility aliases to the moved source-of-truth graph modules.
- Switched the moved run modules to call the moved graph modules directly instead of routing back through legacy graph imports.
- Verified the slice through focused target-tree graph tests, broader target-tree workflow regression tests, representative legacy graph tests, and direct alias identity checks.
- Updated the planning, business, and developer docs plus `workflows/README.md` to reflect the new graph ownership and the temporary compatibility-package path fallback.

## Permission checkpoint

Stop here.

Do **not** start the next TG2 slice or any other follow-up work until the user explicitly approves another run such as:

`/implement-next docs/planning/repo-reorganization/implementation.md docs/planning/repo-reorganization/implementation-handoff.md`
