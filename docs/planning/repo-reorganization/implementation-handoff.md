# Implementation Handoff: Repository Reorganization

- Status: TG1 completed, TG2 in progress, TG3 pending, TG4 pending, TG5 pending
- Last updated: 2026-04-25
- Implementation guide: `docs/planning/repo-reorganization/implementation.md`
- Planning index: `docs/planning/repo-reorganization/index.md`
- Business doc: `docs/business/repo-reorganization/index.md`
- Developer doc: `docs/developer/repo-reorganization/index.md`
- ADR: `docs/planning/adr/ADR-0002-repo-reorganization.md`

## Current status summary

The repository has now completed TG1 plus thirteen TG2 slices: the project-root bootstrap, the shared config/deps move, the shared repo-protection move, the shared fingerprint move, the shared database move, the shared execution-helper move, the shared runtime-deps move, the workflow CLI entry-point move, the workflow graph move, the image-helper-module move, the explicit target-tree state/node-wrapper move, the first bounded image-test-relocation move, and the bounded image-helper-test-relocation move.

What is true after this session:

- `workflows/pipelines/shared/logging.py` remains the tested shared logging foundation for the target tree
- focused shared logging tests still exist under `workflows/tests/shared/test_logging.py`
- `workflows/pyproject.toml` now drives focused target-tree pytest scopes from `workflows/`
- `workflows/.env.example` remains the shared environment-template path for the migration
- `workflows/pipelines/shared/config.py`, `deps.py`, `repo_protection.py`, `fingerprint.py`, `db.py`, `execution.py`, and `runtime_deps.py` are the source-of-truth homes for the moved shared infrastructure modules
- `workflows/pipelines/workflows/image_prompt_gen/run.py` and `workflows/pipelines/workflows/template_upload/run.py` are the source-of-truth workflow entry points
- `workflows/pipelines/workflows/image_prompt_gen/graph.py` and `workflows/pipelines/workflows/template_upload/graph.py` are the source-of-truth workflow graph modules
- `workflows/pipelines/workflows/image_prompt_gen/input_file.py`, `prompts/router_prompts.py`, `prompts/metadata_prompts.py`, `adapters/router_llm.py`, `adapters/image_client.py`, and `pricing.json` remain the moved image-workflow helper surface in the target tree
- `workflows/comicbook/state.py` now exists as an explicit target-tree compatibility wrapper for the still-legacy combined state module
- `workflows/comicbook/nodes/` now exists as an explicit target-tree compatibility wrapper package for the legacy node modules the moved graph layer still relies on
- `workflows/comicbook/__init__.py` still preserves the package-root `upload_templates` convenience export, but no longer extends `comicbook.__path__` into `ComicBook/comicbook`
- target-tree compatibility aliases now exist for the moved shared/run/graph/helper surface plus the new `state` and `nodes/*` bridge wrappers
- `ComicBook/comicbook/input_file.py`, `router_prompts.py`, `metadata_prompts.py`, `router_llm.py`, and `image_client.py` still act as legacy compatibility aliases to the moved helper modules
- focused target-tree compatibility coverage now exists in `workflows/tests/shared/test_compat_state_and_nodes.py`
- bounded target-tree image graph scenario coverage now also exists in `workflows/tests/image_prompt_gen/test_graph_scenarios.py`
- `workflows/tests/image_prompt_gen/support.py` now provides shared target-tree test fixtures and fake transports for the relocated image graph scenarios
- bounded target-tree helper coverage now also exists in `workflows/tests/image_prompt_gen/test_input_file_support.py`, `test_router_validation.py`, and `test_image_client.py`
- broader target-tree regression coverage still exists for runtime-deps, moved helpers, moved graphs, moved runs, relocated image graph scenarios, and relocated non-node image helper tests

What is still true after this session:

- the live tests still reside primarily under `ComicBook/tests/`, even though bounded image graph/helper relocation into `workflows/tests/` has now started
- most workflow-owned node implementations and true state ownership still live under `ComicBook/comicbook/`
- the moved graph modules still execute through legacy-backed node/state bridges; full target-tree workflow execution is not complete yet
- compatibility wrappers now exist for `config`, `deps`, `repo_protection`, `fingerprint`, `db`, `execution`, `runtime_deps`, `state`, `nodes/*`, `input_file`, `router_prompts`, `metadata_prompts`, `router_llm`, `image_client`, `run`, `upload_run`, `graph`, and `upload_graph`, plus the package-root `upload_templates` re-export
- `workflows/pipelines/shared/fingerprint.py` and `workflows/pipelines/shared/db.py` still fall back to legacy `comicbook.state` loading until TG3 moves state ownership cleanly
- `workflows/pipelines/shared/execution.py` still falls back to legacy ingest/state loading until later TG2/TG3 work moves those dependencies cleanly
- `workflows/pipelines/shared/runtime_deps.py` now resolves the target-tree pricing asset first, but still keeps the legacy `ComicBook/comicbook/pricing.json` path as a temporary fallback guard until TG2 cleanup finishes

## TaskGroup status table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Finalize and verify the shared logging foundation | completed | Shared logging module aligned with the standard, covered by focused pytest scope, and documented across the triad. |
| TG2 | Move package and tests into `workflows/` with compatibility wrappers | in progress | Bootstrap plus thirteen TG2 slices are complete: target-tree project metadata landed, seven shared modules now live in `pipelines.shared`, both workflow CLI entry points now live under `pipelines.workflows.*.run`, both workflow graph modules now live under `pipelines.workflows.*.graph`, the image helper modules plus pricing asset now live under `pipelines.workflows.image_prompt_gen.*`, explicit target-tree `comicbook.state` / `comicbook.nodes.*` wrappers now replace the old package-path fallback, and bounded image graph/helper test relocation into `workflows/tests/` has started. Broader test relocation and real runtime ownership moves are still pending. |
| TG3 | Split shared and workflow-specific state modules | pending | Blocked on TG2 completing the package move. |
| TG4 | Complete structured logging adoption and template-upload naming cleanup | pending | Blocked on TG3. |
| TG5 | Remove compatibility layer, promote reused modules, and close out docs | pending | Blocked on TG4. |

## Last completed slice

### Selected TaskGroup and slice

- **TaskGroup:** TG2
- **Slice:** TG2 bounded image-helper-test-relocation move — relocate the already-moved non-node image helper regressions into `workflows/tests/image_prompt_gen/` so target-tree helper behavior is exercised from the new root without changing runtime ownership

### Why this slice size was chosen

The first unfinished TaskGroup remained TG2, and after relocating the image graph scenarios the next high-value adjacent work was the remaining non-node image helper test cluster already called out in the handoff. The local `implementation-slice-guard` skill was present in the repository at `.opencode/skills/implementation-slice-guard/SKILL.md` but was not exposed through the skill tool, so its selection rules were applied manually again. Following that guidance, this slice was chosen because the input-file, router-validation, and image-client tests all target already-moved helper modules, can be re-homed together with one narrow target-tree pytest scope, and still avoid mixing in node-test relocation, template-upload test moves, or TG3 state splitting.

### Completed work from this session

1. Added `workflows/tests/image_prompt_gen/test_input_file_support.py` as target-root coverage for the moved image input-file helpers and CLI batch-entrypoint behavior.
2. Added `workflows/tests/image_prompt_gen/test_router_validation.py` as target-root coverage for the moved router prompt/schema validation helpers.
3. Added `workflows/tests/image_prompt_gen/test_image_client.py` as target-root coverage for the moved image client adapter.
4. Switched those relocated tests to import `pipelines.workflows.image_prompt_gen.*` modules directly, using the target-root `comicbook.state` wrapper only where the moved router helper still depends on the unsplit legacy state models.
5. Verified the new focused target-tree helper-test scope successfully on the first run.
6. Re-ran the broader target-tree image workflow scope plus the matching representative legacy helper regressions successfully.

## Files changed in this session

- `workflows/tests/image_prompt_gen/test_input_file_support.py`
- `workflows/tests/image_prompt_gen/test_router_validation.py`
- `workflows/tests/image_prompt_gen/test_image_client.py`
- `workflows/README.md`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`

## Tests run and results

Focused target-tree relocated image-helper verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen/test_input_file_support.py tests/image_prompt_gen/test_router_validation.py tests/image_prompt_gen/test_image_client.py
```

Result:

- `22 passed in 0.08s`

Broader target-tree image-workflow regression command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/shared/test_runtime_deps.py tests/image_prompt_gen tests/template_upload/test_graph.py tests/template_upload/test_run.py
```

Result:

- `50 passed in 0.99s`

Representative legacy image-helper regression command run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_input_file_support.py tests/test_router_validation.py tests/test_image_client.py
```

Result:

- `22 passed in 0.07s`

Additional verification performed:

- strict TDD was adapted for this relocation slice because these tests were re-homed from already-green legacy coverage rather than created to drive new runtime behavior
- confirmed the relocated helper tests now run from `workflows/` against the moved target-tree image helper modules
- confirmed the broader target-tree image workflow scope still passes with the new relocated helper tests included
- confirmed the matching legacy helper regressions still pass unchanged while the old test files remain in place

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

- no ADR update was needed in this slice because continuing bounded test relocation followed the already accepted migration plan and did not introduce a new architecture decision beyond that plan

## Blockers or open questions

- No code blocker remains for this slice.
- The local `implementation-slice-guard` skill exists in the repository but is not currently loadable through the skill tool, so slice selection used the checked-in skill file directly.
- Direct `pytest` is still unavailable in the shell environment, so verification reused the existing locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- The legacy `ComicBook/comicbook/config.py`, `deps.py`, `repo_protection.py`, `fingerprint.py`, `db.py`, `execution.py`, and `runtime_deps.py` wrappers still add the sibling `workflows/` directory to `sys.path` so the old package root can keep working while TG2 is incomplete. This is a temporary bridge, not the long-term compatibility mechanism.
- `workflows/pipelines/shared/fingerprint.py` still intentionally falls back to the legacy state module for `RenderedPrompt` until TG3 moves state ownership.
- `workflows/pipelines/shared/db.py` still intentionally falls back to the legacy state module for `TemplateSummary` until TG3 moves state ownership.
- `workflows/pipelines/shared/execution.py` still intentionally falls back to the legacy state and ingest modules even though target-tree wrappers now exist; that helper should be cleaned up in a later TG2/TG3 slice when ownership fully moves.
- `workflows/pipelines/shared/runtime_deps.py` still keeps the legacy `ComicBook/comicbook/pricing.json` path as a fallback guard even though the target-tree pricing asset now exists. That fallback should disappear during later TG2/TG5 cleanup.
- the legacy `ComicBook/tests/test_graph_happy.py`, `test_graph_cache_hit.py`, `test_graph_resume.py`, and `test_graph_new_template.py` files still remain in place for now from the prior slice; delete operations are still approval-gated and later TG2 cleanup will decide when to retire them.
- the legacy `ComicBook/tests/test_input_file_support.py`, `test_router_validation.py`, and `test_image_client.py` files also still remain in place for now; this slice added target-tree equivalents but intentionally did not remove the old files because TG2 cleanup is still pending and delete operations are approval-gated.
- Running Python verification touched tracked and untracked `__pycache__` artifacts under `workflows/`; they were left in place because delete/revert cleanup is approval-gated in this workflow.

## Exact next recommended slice

### TG2 next slice: continue bounded template-upload test relocation into `workflows/tests/`

Recommended next implementation slice:

1. relocate one bounded set of already-migrated template-upload tests from `ComicBook/tests/` into `workflows/tests/template_upload/`, most likely the upload graph and CLI regression tests
2. update imports and shared test helpers only as needed so those relocated tests run from the target root without changing workflow behavior
3. keep the slice limited to template-upload test ownership and path cleanup; do not mix in runtime module moves or upload node-test relocation yet
4. verify the relocated template-upload tests from `workflows/` first, then run a representative legacy upload regression scope while the old files still remain

Why this next slice is recommended:

- TG2 is still the first unfinished TaskGroup, and after two bounded image-workflow relocation batches the next already-moved runtime surface with remaining legacy tests is template upload's run/graph layer
- template-upload graph and CLI tests target modules that already have target-tree homes, so they are the next natural relocation candidates
- keeping upload node-owned tests out of the next slice avoids mixing test relocation with still-legacy node ownership

Boundaries for the next session:

- do not start TG3+
- do not move workflow node implementations in the same slice as template-upload test relocation
- do not remove legacy paths yet
- keep relocation scoped to one bounded template-upload test cluster; leave upload node tests and delete cleanup for later slices

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

### 2026-04-25 — TG2 image-helper-module implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill guidance to choose the next eligible commit-sized slice after the workflow-graph move.
- Loaded and applied `pytest-tdd-guard` because moving the helper modules and pricing asset behind compatibility aliases is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed developer-facing import ownership, pricing-asset resolution, and maintainer-facing migration status.
- Added focused target-tree tests first; the initial run failed because the target-tree image helper modules did not exist yet and because `_default_pricing_path()` still resolved the legacy pricing asset first.
- Added the target-tree source-of-truth helper modules under `workflows/pipelines/workflows/image_prompt_gen/`, including `input_file.py`, prompt helpers, adapter helpers, and `pricing.json`.
- Added target-tree compatibility aliases for `comicbook.input_file`, `router_prompts`, `metadata_prompts`, `router_llm`, and `image_client`.
- Converted the legacy `ComicBook/comicbook/input_file.py`, `router_prompts.py`, `metadata_prompts.py`, `router_llm.py`, and `image_client.py` modules into compatibility aliases to the moved source-of-truth helper modules.
- Switched the moved image entry point to import its input-file helpers directly from the moved target-tree helper module.
- Verified the slice through focused target-tree helper tests, broader target-tree image-workflow regression tests, and representative legacy helper/node/workflow tests.
- Updated the planning, business, and developer docs plus `workflows/README.md` to reflect the new helper ownership and target-tree pricing-asset resolution.

### 2026-04-25 — TG2 explicit state-and-node-wrapper implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill guidance to choose the next eligible commit-sized slice after the image-helper-module move.
- Loaded and applied `pytest-tdd-guard` because replacing the package-path fallback with explicit wrappers is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed compatibility-wrapper behavior and maintainer-facing migration status.
- Added focused target-tree tests first; the initial run failed because `workflows/comicbook/__init__.py` still appended `ComicBook/comicbook` to `comicbook.__path__` and because explicit target-tree `state` / `nodes` wrappers did not exist yet.
- Added `workflows/comicbook/state.py` plus `workflows/comicbook/nodes/` wrapper modules as explicit target-tree bridges to the still-legacy state and node modules.
- Removed the old compatibility-package path fallback from `workflows/comicbook/__init__.py` while keeping the package-root `upload_templates` convenience export.
- Verified the slice through focused target-tree compatibility tests, a broader target-tree moved-module regression scope, representative legacy node/graph regressions, and a direct alias identity check.
- Updated the planning, business, and developer docs plus `workflows/README.md` to reflect that TG2 now uses explicit `state` / `nodes` wrappers instead of hidden package-path fallback.

### 2026-04-25 — TG2 bounded image-test-relocation implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill guidance to choose the next eligible commit-sized slice after the explicit state/node-wrapper move.
- Loaded and applied `docs-update-guard` because the slice changed developer-facing test layout and migration-status documentation.
- Started bounded TG2 test relocation with the legacy image graph scenario coverage because those tests target a workflow graph module that already has a target-tree source of truth.
- Added `workflows/tests/image_prompt_gen/test_graph_scenarios.py` and `workflows/tests/image_prompt_gen/support.py` so those scenarios can run from `workflows/` against `pipelines.workflows.image_prompt_gen.graph` and the moved shared helpers.
- The first focused target-tree run failed because the new test module referenced a `db` fixture that had not been imported from the shared support module yet; importing that fixture was the only code change needed to turn the scope green.
- Verified the slice through the focused relocated-test scope, a broader target-tree image workflow scope, and the matching legacy image graph regressions.
- Updated the planning, business, and developer docs plus `workflows/README.md` to record that bounded test relocation into `workflows/tests/` has now started.

### 2026-04-25 — TG2 bounded image-helper-test-relocation implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill guidance to choose the next eligible commit-sized slice after the first bounded image graph test relocation.
- Loaded and applied `docs-update-guard` because the slice changed developer-facing test layout and migration-status documentation.
- Added `workflows/tests/image_prompt_gen/test_input_file_support.py`, `test_router_validation.py`, and `test_image_client.py` as the next bounded relocation cluster for already-moved non-node image-workflow helper modules.
- Switched the relocated tests to import the moved target-tree helper modules directly, while continuing to rely on `comicbook.state` only where the unsplit legacy state models are still the source of truth.
- Verified the slice through the focused relocated-helper scope, a broader target-tree image workflow scope, and the matching legacy helper regressions.
- Updated the planning, business, and developer docs plus `workflows/README.md` to record that bounded image-helper test relocation into `workflows/tests/` is now in place.

## Permission checkpoint

Stop here.

Do **not** start the next TG2 slice or any other follow-up work until the user explicitly approves another run such as:

`/implement-next docs/planning/repo-reorganization/implementation.md docs/planning/repo-reorganization/implementation-handoff.md`
