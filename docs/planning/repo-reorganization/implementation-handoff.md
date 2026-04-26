# Implementation Handoff: Repository Reorganization

| Field | Value |
| --- | --- |
| Status | TG1 completed; TG2 completed; TG3 completed; TG4 completed; TG5 in progress (verification blocked) |
| Last updated | 2026-04-26 |
| Active implementation guide | `docs/planning/repo-reorganization/implementation-v2.md` |
| Preserved prior guide | `docs/planning/repo-reorganization/implementation.md` (historical; superseded by v2 — kept on disk for traceability of earlier execution) |
| Source plan | `docs/planning/repo-reorganization/plan.md` |
| Planning index | `docs/planning/repo-reorganization/index.md` |
| Business doc | `docs/business/repo-reorganization/index.md` |
| Developer doc | `docs/developer/repo-reorganization/index.md` |
| ADR | `docs/planning/adr/ADR-0002-repo-reorganization.md` (status: **Accepted and Implemented**, updated during TG5 closeout work) |

> The `/implementation-doc` command was re-run on 2026-04-25 with stricter quality requirements; the resulting `implementation-v2.md` is now authoritative. Going forward, every slice references the canonical task IDs from v2 (`TG{N}-T{M}`). Previously completed work is mapped to those IDs in the table below so no execution detail is lost.

## Current status summary

The shared logging foundation landed under TG1 and has remained stable. TG2 is complete and remains green. TG3 is complete and remains green. TG4 is complete and remains green. TG5 cleanup has now landed in code: the `comicbook` shim trees were removed, package discovery is narrowed to `pipelines*`, shared metadata-backfill and Responses helpers were promoted into `pipelines.shared`, tests/examples now import `pipelines.*` directly, and active docs/tooling point at the final layout.

What is **not yet** done overall: the guide-required TG5 verification gate is blocked. After removing the old locked `ComicBook` uv project as part of approved cleanup, the replacement `workflows/` project has no synced pytest environment yet, so the final full pytest run and CLI smoke checks now require explicit install/sync approval before TG5 can be marked complete.

## TaskGroup progress table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Shared logging foundation | completed | `workflows/pipelines/shared/logging.py` matches the standard; covered by `workflows/tests/shared/test_logging.py`. ADR-0002 set to **Accepted**. |
| TG2 | Move package + tests into `workflows/`, add `comicbook` shim, normalize doc slugs, adopt non-node logging | completed | TG2-T1 through TG2-T13 are complete. Full target-tree pytest exit gate passed; docs gate closed. |
| TG3 | Split state modules | completed | TG3-T1 through TG3-T8 are complete. State ownership is split cleanly and boundary tests plus full pytest passed. |
| TG4 | Adopt node logging + remove `upload_` prefix | completed | TG4-T1 through TG4-T8 are effectively complete: logging adoption, rename/wrapper updates, verification, and docs are all green. |
| TG5 | Remove the `comicbook` shim and close the migration | in progress (verification blocked) | TG5.T1-T4 and most of TG5.T6-T8 landed; final pytest/CLI verification needs install approval after deleting the old locked uv project. |

### TG2 sub-task map (canonical IDs from `implementation-v2.md`)

| Task | Status | Evidence |
| --- | --- | --- |
| TG2-T1 — finalize `workflows/pyproject.toml` | completed | `workflows/pyproject.toml` drives target-tree pytest from `workflows/`; package discovery includes both `pipelines*` and `comicbook*`; `pythonpath = ["."]` in place. |
| TG2-T2 — move `.env.example` | completed | `git mv ComicBook/.env.example workflows/.env.example` landed; references updated. |
| TG2-T3 — move shared modules | completed | `pipelines/shared/{config,deps,repo_protection,fingerprint,db,execution,runtime_deps}.py` are the source-of-truth homes. Legacy `ComicBook/comicbook/*.py` modules converted to thin wrappers. Target-tree wrappers exist under `workflows/comicbook/`. Temporary state-fallbacks remain in `fingerprint.py`, `db.py`, `execution.py`, and a temporary pricing-path fallback remains in `runtime_deps.py`; all are scheduled for TG3/TG5 cleanup. |
| TG2-T4 — move workflow entry points + graphs | completed | `pipelines/workflows/image_prompt_gen/{run,graph}.py` and `pipelines/workflows/template_upload/{run,graph}.py` are the source-of-truth modules. Run-module wrappers use module-alias compatibility (Pattern 2) to preserve monkey-patch identity. |
| TG2-T5 — move image-workflow helpers | completed | `pipelines/workflows/image_prompt_gen/{input_file.py,prompts/router_prompts.py,prompts/metadata_prompts.py,adapters/router_llm.py,adapters/image_client.py,pricing.json}` moved. Legacy modules and target-tree wrappers exist. Default pricing-path resolution prefers the target-tree asset with a temporary legacy fallback. |
| TG2-T6 — move nodes (mechanical) | completed | Explicit wrappers exist under `workflows/comicbook/nodes/` and `workflows/comicbook/state.py`. All image nodes now live under `pipelines/workflows/image_prompt_gen/nodes/`; all template-upload nodes now live under `pipelines/workflows/template_upload/nodes/`; both workflow graph modules import their target-tree nodes directly while legacy module paths remain compatibility aliases. |
| TG2-T7 — move adjacent assets (`examples/`, `DoNotChange/`) | completed | `ComicBook/examples/` → `workflows/examples/` and `ComicBook/DoNotChange/` → `workflows/DoNotChange/` moved with `git mv`; `pipelines.shared.repo_protection`, target-tree and legacy repo-protection tests, example continuity coverage, README notes, and repo-reorganization docs now reference the new paths. |
| TG2-T8 — adopt non-node structured logging | completed | `pipelines.shared.runtime_deps` uses the shared logger helper and both moved run modules emit lifecycle events via `log_event(...)`; existing target-tree run tests and runtime-deps tests cover the adopted surface. |
| TG2-T9 — relocate tests | completed | The final unique legacy regression moved to `workflows/tests/image_prompt_gen/test_router_node.py`, the remaining unique dotenv-override assertion moved into `workflows/tests/shared/test_config_and_deps.py`, duplicate legacy `ComicBook/tests/test_*.py` files were removed after verification, approved `__pycache__` artifacts were cleaned, and the now-empty `ComicBook/tests/` directory was deleted. |
| TG2-T10 — normalize doc-tree slugs | completed | The image-workflow planning, business, and developer doc folders now use `image-prompt-gen-workflow`; top-level indexes, related planning/docs references, ADR links, and implementation-execution examples were updated; grep for the legacy mixed-case slug is now empty. |
| TG2-T11 — update tooling references | completed | `AGENTS.md`, `.opencode/agents/test-engineer.md`, and `.opencode/agents/langgraph-architect.md` now treat `workflows/` / `workflows/tests/` as canonical while describing `ComicBook/comicbook/` only as transitional compatibility surface; `opencode.json` required no change and `.pre-commit-config.yaml` still intentionally points at the legacy protection script path that remains live during the shim window. |
| TG2-T12 — run full target-tree test suite | completed | `uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared`, `tests/image_prompt_gen`, `tests/template_upload`, and full `pytest -q` all passed from `workflows/`; the full suite finished at `165 passed`. |
| TG2-T13 — TG2 documentation gate | completed | Repo-reorganization planning/business/developer docs plus `workflows/README.md` now describe `workflows/` as the active project root, the `comicbook` shim as transitional, normalized workflow doc slugs, and non-node logging adoption. |

### TG3 sub-task map (canonical IDs from `implementation-v2.md`)

| Task | Status | Evidence |
| --- | --- | --- |
| TG3-T1 — create `pipelines/shared/state.py` | completed | `workflows/pipelines/shared/state.py` now owns `WorkflowModel`, `WorkflowError`, `UsageTotals`, `RunSummary`, and `RunStatus` with explicit `__all__`. |
| TG3-T2 — create image-workflow state module | completed | `workflows/pipelines/workflows/image_prompt_gen/state.py` now owns `RunState`, `TemplateSummary`, router models, prompt models, and image-result models. |
| TG3-T3 — create template-upload state module | completed | `workflows/pipelines/workflows/template_upload/state.py` now owns `ImportRunState`, `TemplateImportRow`, `TemplateImportRowResult`, `ImportRowStatus`, and `ImportWriteMode`. |
| TG3-T4 — rewire importers | completed | Workflow graphs, nodes, prompts, adapters, shared helpers, examples, and tests now import state symbols from the correct split module instead of `comicbook.state`. |
| TG3-T5 — update `workflows/comicbook/state.py` wrapper | completed | Both `workflows/comicbook/state.py` and `ComicBook/comicbook/state.py` now re-export the split symbols and preserve the legacy surface without duplicate definitions. |
| TG3-T6 — sanity-check state-import boundaries | completed | Boundary greps for shared→workflow and cross-workflow state imports all returned empty; `workflows/tests/shared/test_state_boundaries.py` now enforces the rule. |
| TG3-T7 — run pytest | completed | Focused state, focused regression, per-workflow, and full target-tree pytest scopes all passed from `workflows/`; the final full suite finished at `171 passed`. |
| TG3-T8 — documentation update | completed | `docs/planning/repo-reorganization/index.md`, `docs/developer/repo-reorganization/index.md`, and this handoff now record the completed state split and TG4 as next. |

### TG4 sub-task map (canonical IDs from `implementation-v2.md`)

| Task | Status | Evidence |
| --- | --- | --- |
| TG4-T1 — sweep for node-level direct logging | completed | Greps across `workflows/pipelines/workflows/` found no remaining `deps.logger.*` or `logging.getLogger(...)` usage inside workflow runtime code. |
| TG4-T2 — convert node emit sites | completed | Every image-workflow node, every template-upload node, and the graph-local helper nodes are now wrapped by workflow-specific instrumentation decorators that emit `node_started`, `node_completed`, and `node_failed` through `log_node_event(...)`. |
| TG4-T3 — rename template-upload nodes | completed | The seven template-upload source-of-truth node modules were renamed to unprefixed names and their primary callables plus graph node names/imports were updated accordingly. |
| TG4-T4 — update `comicbook/nodes/upload_*.py` wrappers | completed | Both `workflows/comicbook/nodes/upload_*.py` and `ComicBook/comicbook/nodes/upload_*.py` now re-export the renamed targets while preserving the legacy callable names. |
| TG4-T5 — add focused logging tests | completed | Added `workflows/tests/image_prompt_gen/test_graph_logging.py` and `workflows/tests/template_upload/test_graph_logging.py` for representative successful runs plus targeted failing-node logging cases. |
| TG4-T6 — run tests in layers | completed | `-k log`, shared+workflow regression, and full `pytest -q` all passed from `workflows/`; final suite stayed green at `175 passed`. |
| TG4-T7 — capture representative sample run output | completed | The new logging tests execute representative end-to-end runs, capture real stdout JSON logs, parse them, and assert the required fields for both workflows. |
| TG4-T8 — documentation gate | completed | Planning/business/developer repo-reorganization docs and this handoff now record both logging adoption and template-upload naming cleanup, with TG5 as next. |

### TG5 sub-task map (canonical IDs from `implementation-v2.md`)

| Task | Status | Evidence |
| --- | --- | --- |
| TG5-T1 — final sweep before deletion | completed | `grep` under `workflows/` found no remaining functional `comicbook` imports before deletion work; active tests/examples were rewired to `pipelines.*`; `examples/single_portrait_graph.py`, shared execution/runtime deps, and active workflow docs/tooling no longer depend on shim paths. |
| TG5-T2 — delete the compatibility shim | completed | Deleted the tracked `workflows/comicbook/**`, `ComicBook/**`, and `workflows/tests/shared/test_compat_state_and_nodes.py` surfaces; follow-up filesystem checks confirm both directories now do not exist. |
| TG5-T3 — update package discovery | completed | `workflows/pyproject.toml` now narrows setuptools discovery to `include = ["pipelines*"]`. |
| TG5-T4 — promote shared modules where needed | completed | Added `workflows/pipelines/shared/responses.py` and `workflows/pipelines/shared/metadata_backfill.py`; rewired template-upload metadata backfill and image-workflow router helpers so cross-workflow ownership now lives in `pipelines.shared`. |
| TG5-T5 — run the full test suite | blocked | `python3 -m py_compile` over the changed Python files succeeded, but the required pytest run is blocked because deleting the old locked `ComicBook` uv project removed the only available local pytest environment; `uv run --project "." --no-sync pytest ...` now fails with `Failed to spawn: pytest`. |
| TG5-T6 — documentation gate | in progress | Active workflow docs, repo-structure standards, AGENTS/agent docs, README, repo-reorganization docs, and ADR status were refreshed to the final layout; final completion wording still depends on the blocked TG5 verification gate. |
| TG5-T7 — update ADR-0002 | completed | `docs/planning/adr/ADR-0002-repo-reorganization.md` now reads **Accepted and Implemented** and records the TG5 close date. |
| TG5-T8 — update the implementation-handoff ledger | in progress | This ledger now records the TG5 cleanup work and the verification blocker, but the final "Migration complete" entry is deferred until TG5-T5 passes. |

## Current in-progress slice

### Selected TaskGroup and slice cluster

- **TaskGroup:** TG5
- **Slice cluster:** TG5-T1 through TG5-T4 plus the non-final portions of TG5-T6 through TG5-T8
- **Canonical IDs under v2:** TG5-T1, TG5-T2, TG5-T3, TG5-T4, partial TG5-T6, partial TG5-T8, and TG5-T7

### Why these slice boundaries were chosen

After TG4, the remaining guide-ordered work was one tightly related cleanup cluster: remove the shim trees, rewire the few remaining direct dependents, promote cross-workflow helpers into `pipelines.shared`, narrow package discovery, and refresh active docs/tooling. The user explicitly approved the delete-heavy TG5 cleanup slice, so it was safe to complete that cluster in one pass. The session stopped only when the guide-required final pytest/CLI verification hit a new approval gate for dependency installation/sync.

### Completed work from this session

- Rewired remaining functional references away from `comicbook.*`, including the shared execution helper, runtime pricing-path lookup, the single-portrait example, and active workflow tests.
- Promoted cross-workflow Responses transport helpers into `workflows/pipelines/shared/responses.py` and metadata-backfill prompt/schema helpers into `workflows/pipelines/shared/metadata_backfill.py`.
- Deleted the tracked compatibility shim surfaces under `workflows/comicbook/` and `ComicBook/`, removed the compat smoke test, and removed the remaining on-disk untracked shim directories.
- Narrowed setuptools package discovery to `pipelines*` only.
- Updated active workflow docs, repo-structure standards, AGENTS/agent docs, README, repo-reorganization indexes, and ADR-0002 to reflect the final target layout.
- Captured the new verification blocker: the old locked `ComicBook` uv project was removed during approved cleanup, so no synced local pytest environment remains for the guide-required TG5 exit gate.

### Files changed in this session

- Added: `workflows/pipelines/shared/responses.py`
- Added: `workflows/pipelines/shared/metadata_backfill.py`
- Deleted: `workflows/comicbook/**`
- Deleted: `ComicBook/**`
- Deleted: `workflows/tests/shared/test_compat_state_and_nodes.py`
- Deleted: `workflows/pipelines/workflows/image_prompt_gen/prompts/metadata_prompts.py`
- Modified active runtime/test/doc/tooling files across `workflows/pipelines/`, `workflows/tests/`, `docs/`, `AGENTS.md`, `.opencode/agents/`, `.pre-commit-config.yaml`, `workflows/README.md`, and `workflows/pyproject.toml`

### Tests run and results in this session

- `python3 -m py_compile ...` across the changed Python modules and tests → **passed** (no syntax errors)
- `grep` for `from comicbook|import comicbook` under `workflows/` → **no matches**
- `read` checks for `/ComicBook` and `/workflows/comicbook` after cleanup → **both paths missing**
- `uv run --project "." --no-sync pytest -c pyproject.toml -q ...` from `workflows/` → **blocked**, failed immediately with `Failed to spawn: pytest` because the local `workflows/` uv environment has not been synced and the deleted `ComicBook` project no longer provides pytest

### Documentation updated in this session

- The docs-update gate applied because TG5 changes the repository-wide runtime layout, active package paths, tooling commands, and developer/operator expectations.
- Updated active workflow business/developer docs to use `pipelines.*` commands and module paths.
- Updated `docs/standards/repo-structure.md`, `AGENTS.md`, `.opencode/agents/test-engineer.md`, `.opencode/agents/langgraph-architect.md`, and `workflows/README.md` to remove shim-era guidance and document the promoted shared modules.
- Updated repo-reorganization planning/business/developer indexes plus this handoff to record the landed cleanup work and the remaining verification blocker.
- Updated ADR-0002 status to **Accepted and Implemented**.

### Current blockers or open questions

- Final TG5 verification is blocked on explicit approval to install/sync dependencies for the `workflows/` uv project (or another equivalent package-install action) so pytest can run after the old `ComicBook` environment was removed.
- The local `implementation-slice-guard` skill still exists on disk but is not loadable through the skill tool, so slice selection continues to apply the checked-in rules manually.

### Exact next recommended slice

1. Explicitly approve dependency installation/sync for `workflows/`.
2. Run the guide-required TG5 verification:
   - full `pytest -q` from `workflows/`
   - representative CLI help/invocation smoke checks for both workflows
3. If those pass, finish TG5-T6/TG5-T8 wording and add the final "Migration complete" session entry.

## Last completed slices

### Selected TaskGroup and slices

- **TaskGroup:** TG4
- **Slice cluster:** TG4-T3, TG4-T4, and TG4-T8 as one rename/wrapper closeout session after the earlier logging-adoption slice
- **Canonical IDs under v2:** TG4-T3, TG4-T4, and TG4-T8

### Why these slice boundaries were chosen

After the earlier TG4 logging-adoption slice, the remaining TG4 work was one tightly related closeout cluster: rename the template-upload source-of-truth nodes/functions, update graph assembly, preserve the legacy wrapper API, and refresh the docs/handoff once the runtime and tests were green. The user explicitly approved the rename/delete-like file operations needed for this slice, so it was safe to complete the rest of TG4 as one coherent increment.

### Completed work from this session

- Renamed the seven template-upload source-of-truth node modules to `load_file.py`, `parse_and_validate.py`, `resume_filter.py`, `backfill_metadata.py`, `decide_write_mode.py`, `persist.py`, and `summarize.py`.
- Renamed the primary callables in those modules to the matching unprefixed names and removed the remaining `upload_*` runtime strings from the target-tree template-upload package.
- Updated `workflows/pipelines/workflows/template_upload/graph.py` so graph imports, graph node names, edges, and routing use the unprefixed runtime names.
- Replaced both compatibility-wrapper layers with explicit re-export wrappers so `comicbook.nodes.upload_*` and `ComicBook.comicbook.nodes.upload_*` still expose the legacy callable names while targeting the renamed modules.
- Updated compatibility and logging tests so they now reference the renamed target-tree modules while still validating legacy wrapper behavior.
- Updated the repo-reorganization planning/business/developer docs and this handoff to mark TG4 complete and point the next session at TG5 cleanup.

## Files changed in this session

- `ComicBook/comicbook/nodes/upload_backfill_metadata.py`
- `ComicBook/comicbook/nodes/upload_decide_write_mode.py`
- `ComicBook/comicbook/nodes/upload_load_file.py`
- `ComicBook/comicbook/nodes/upload_parse_and_validate.py`
- `ComicBook/comicbook/nodes/upload_persist.py`
- `ComicBook/comicbook/nodes/upload_resume_filter.py`
- `ComicBook/comicbook/nodes/upload_summarize.py`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`
- `docs/planning/repo-reorganization/index.md`
- `workflows/comicbook/nodes/upload_backfill_metadata.py`
- `workflows/comicbook/nodes/upload_decide_write_mode.py`
- `workflows/comicbook/nodes/upload_load_file.py`
- `workflows/comicbook/nodes/upload_parse_and_validate.py`
- `workflows/comicbook/nodes/upload_persist.py`
- `workflows/comicbook/nodes/upload_resume_filter.py`
- `workflows/comicbook/nodes/upload_summarize.py`
- `workflows/pipelines/workflows/template_upload/graph.py`
- `workflows/pipelines/workflows/template_upload/nodes/backfill_metadata.py`
- `workflows/pipelines/workflows/template_upload/nodes/decide_write_mode.py`
- `workflows/pipelines/workflows/template_upload/nodes/load_file.py`
- `workflows/pipelines/workflows/template_upload/nodes/parse_and_validate.py`
- `workflows/pipelines/workflows/template_upload/nodes/persist.py`
- `workflows/pipelines/workflows/template_upload/nodes/resume_filter.py`
- `workflows/pipelines/workflows/template_upload/nodes/summarize.py`
- `workflows/tests/shared/test_compat_state_and_nodes.py`
- `workflows/tests/template_upload/test_graph_logging.py`

## Tests run and results

Focused rename/wrapper regression scope from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/template_upload/test_node_preflight.py tests/template_upload/test_node_backfill_metadata.py tests/template_upload/test_node_persist.py tests/template_upload/test_graph_scenarios.py tests/template_upload/test_graph_logging.py
```

Result: `36 passed in 0.77s`.

Guide-ordered TG4 logging scope rerun from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload tests/image_prompt_gen -k log
```

Result: `10 passed, 97 deselected in 0.49s`.

Broader regression scope from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared tests/image_prompt_gen tests/template_upload
```

Result: `175 passed in 5.48s`.

Full target-tree suite from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q
```

Result: `175 passed in 5.48s`.

Runtime grep verification:

- `grep` for `deps.logger.*` or `logging.getLogger` under `workflows/pipelines/workflows/` → no matches
- `grep` for `upload_load_file|upload_parse_and_validate|upload_resume_filter|upload_backfill_metadata|upload_decide_write_mode|upload_persist|upload_summarize` under `workflows/pipelines/workflows/template_upload/` → no matches

## Documentation updated

- The docs-update gate applied because this slice changed developer-facing runtime naming and compatibility behavior, and it completed TG4's user/operator-observable logging and naming contracts.
- Updated `docs/planning/repo-reorganization/index.md` to mark TG4 complete and TG5 next.
- Updated `docs/business/repo-reorganization/index.md` to note that the live template-upload runtime now uses unprefixed internal node names while the compatibility layer keeps legacy `upload_*` imports working.
- Updated `docs/developer/repo-reorganization/index.md` with the completed rename slice, graph rewires, wrapper strategy, and TG5 as next.
- Updated this handoff ledger to mark TG4 complete, record the approved rename slice, and recommend the TG5 cleanup checkpoint.
- No ADR or logging standard update was needed because the implementation follows the existing approved repository and logging contracts without adding new fields or architecture changes.

## Blockers or open questions

- The local `implementation-slice-guard` skill exists on disk at `.opencode/skills/implementation-slice-guard/SKILL.md` but is still not loadable through the skill tool, so slice selection continues to apply the checked-in rules manually.
- Direct `pytest` is still unavailable in the shell environment; verification continues to use the locked `ComicBook` uv project with `--no-sync`.
- The pytest runs continue to regenerate tracked and untracked `__pycache__/` artifacts under `workflows/`; deleting those cache files still requires explicit approval because it is a delete operation.
- `pipelines.shared.runtime_deps` still keeps the legacy `ComicBook/comicbook/pricing.json` path as a fallback; that cleanup belongs to later migration work.
- TG5 is entirely cleanup-heavy and includes recursive shim removal, smoke-test deletion, and legacy-reference cleanup, so it remains approval-sensitive under the repository rules.
- No technical blocker remains from TG4 itself.

## Exact next recommended slice

**Recommended TaskGroup:** TG5.

**Recommended task focus:** begin TG5 with the final sweep and compatibility-shim removal planning checkpoint: validate the remaining `comicbook` references, then remove `workflows/comicbook/`, `ComicBook/`, and the compat smoke tests only after explicit approval for the delete-heavy cleanup slice.

**Why this slice:**

- TG4 is complete and green.
- TG5 is the next incomplete guide-ordered TaskGroup.
- The remaining work is now almost entirely cleanup, legacy-reference removal, package-discovery narrowing, and final docs/ADR closeout.

**Boundaries for the next session:**

- do not start TG5 until delete approval for the shim-removal slice is explicit;
- keep the first TG5 slice focused on the shim/remnant cleanup and direct importer rewires only;
- finish with the full pytest run and final docs/ADR updates once the cleanup lands.

## Session log

### 2026-04-24 — Planning session

- Created the original `docs/planning/repo-reorganization/implementation.md` as the primary implementation document.
- Created the initial `docs/planning/repo-reorganization/implementation-handoff.md` ledger.
- Updated planning indexes for the new implementation material. No runtime code changed.

### 2026-04-25 — TG1 implementation session

- Reviewed the implementation guide, current handoff, `workflows/pipelines/shared/logging.py`, the logging standard, and the local `implementation-slice-guard` instructions.
- Loaded `pytest-tdd-guard` because the slice changed Python behavior in the shared logging module; loaded `docs-update-guard` because the slice materially changed observability infrastructure and developer-facing migration status.
- Completed TG1 as one cohesive slice. Added focused logging tests; ran the TG1 pytest scope successfully.
- Updated planning, business, developer docs and ADR-0002 to reflect that implementation has started and TG1 is complete.

### 2026-04-25 — TG2 bootstrap (TG2-T1, TG2-T2)

- Added `workflows/pyproject.toml` and configured target-tree package discovery plus pytest settings; moved `.env.example`. First focused run exposed that `pipelines` was not importable during pytest collection from `workflows/`; added `pythonpath = ["."]` to the new pyproject.

### 2026-04-25 — TG2 shared config/deps move (TG2-T3 partial)

- Added focused target-tree test first; the initial run failed because `pipelines.shared.config` and `deps` did not exist yet. Added the new modules; converted legacy `ComicBook/comicbook/{config,deps}.py` to thin wrappers; added matching wrappers under `workflows/comicbook/`. Re-ran target-tree and legacy regression scopes successfully.

### 2026-04-25 — TG2 repo-protection move (TG2-T3)

- Added `pipelines.shared.repo_protection` and matching wrappers; legacy module became a thin wrapper. Verified through focused target-tree tests, the legacy CLI script path, and the legacy repo-protection regression scope.

### 2026-04-25 — TG2 fingerprint move (TG2-T3)

- Added `pipelines.shared.fingerprint` and matching wrappers. Kept a temporary fallback to legacy `RenderedPrompt` until TG3 lands. Verified through focused target-tree tests and broader shared-module regression scopes.

### 2026-04-25 — TG2 database move (TG2-T3)

- Added `pipelines.shared.db` and matching wrappers; kept a temporary fallback to legacy `TemplateSummary` until TG3 lands. Verified through focused target-tree tests, broader target-tree shared regression, and representative legacy image and template-upload smoke tests.

### 2026-04-25 — TG2 execution move (TG2-T3)

- Added `pipelines.shared.execution` and matching wrappers; kept temporary fallbacks to legacy ingest/state modules. Verified through focused target-tree tests, broader target-tree shared regression, and representative legacy image, template-upload, and example smoke tests.

### 2026-04-25 — TG2 runtime-deps move (TG2-T3 + TG2-T8 partial)

- Added `pipelines.shared.runtime_deps`. Switched managed dependency construction to `get_logger(__name__)`. Kept a temporary fallback to the legacy pricing asset. Expanded focused coverage in `workflows/tests/shared/test_runtime_deps.py`. Verified through focused target-tree tests, broader target-tree shared regression, a direct import check for `comicbook.upload_templates`, and representative legacy runtime-entrypoint regressions.

### 2026-04-25 — TG2 CLI entry-point move (TG2-T4 partial + TG2-T8 partial)

- Added `pipelines.workflows.image_prompt_gen.run` and `pipelines.workflows.template_upload.run`. Added target-tree compatibility aliases for `comicbook.run`, `comicbook.upload_run`, and `comicbook.input_file`. Discovered that plain symbol re-exports broke monkey-patch-based tests; switched run-module wrappers to module aliases (Pattern 2). Adopted `log_event(...)` lifecycle calls in the moved run modules.

### 2026-04-25 — TG2 workflow-graph move (TG2-T4)

- Added `pipelines.workflows.image_prompt_gen.graph` and `pipelines.workflows.template_upload.graph`. Added wrappers; converted legacy graph modules to compatibility aliases. Switched the moved run modules to import from the moved graph modules directly.

### 2026-04-25 — TG2 image-helper-module move (TG2-T5)

- Added target-tree image helpers under `pipelines.workflows.image_prompt_gen/{input_file.py,prompts/*,adapters/*,pricing.json}`. Added matching wrappers. Switched the moved image entry point to import helpers directly from the moved modules. Pricing-path resolution prefers the target-tree asset with a temporary legacy fallback.

### 2026-04-25 — TG2 explicit state-and-node-wrapper move (TG2-T6 partial)

- Replaced the package-path fallback with explicit `workflows/comicbook/state.py` and `workflows/comicbook/nodes/*` wrapper modules. Removed the old `comicbook.__path__` extension. Verified through focused compatibility tests, broader target-tree regression, representative legacy node/graph regressions, and identity checks. (Note: actual node implementations still live under `ComicBook/comicbook/nodes/`; only wrappers exist in the target tree.)

### 2026-04-25 — TG2 bounded test relocations (TG2-T9, multiple sessions)

- Bounded relocation across shared, image-prompt-gen, and template-upload subtrees: image graph scenarios, image helpers (input file support, router validation, image client), template-upload graph + run-CLI, image budget-guard, shared config + state-contract continuity, image example-single-portrait continuity, shared fingerprint expansion, image node-wrapper continuity (ingest + summarize), template-upload preflight nodes (load_file, parse_and_validate, resume_filter, decide_write_mode), template-upload backfill node, template-upload persist node. Each slice ran the focused new scope, the broader target-tree regression scope, and a matching legacy regression scope.

### 2026-04-25 — TG2 bounded image `load_templates` test relocation

- Manually applied the checked-in `implementation-slice-guard` rules and selected the smallest next TG2 slice: wrapper-backed continuity coverage for `comicbook.nodes.load_templates`.
- Added `workflows/tests/image_prompt_gen/test_node_load_templates.py` using target-tree shared imports plus the explicit compatibility wrapper for the still-legacy node module.
- Verified the focused target-tree scope, broader target-tree image-workflow regression scope, and matching legacy regression scope; all green.

### 2026-04-25 — TG2 bounded image `cache_lookup` test relocation

- Re-ran manual `implementation-slice-guard` selection and kept TG2-T9 narrowly scoped to the next image node with meaningful persistence behavior but no delete/copy/install requirement.
- Added `workflows/tests/image_prompt_gen/test_node_cache_lookup.py` using target-tree shared imports plus the explicit compatibility wrapper for the still-legacy node module.
- Verified the focused target-tree scope, broader target-tree image-workflow regression scope, and matching legacy regression scope; all green.

### 2026-04-25 — TG2 first actual image-node moves (`load_templates`, `cache_lookup`, `router`)

- Loaded `pytest-tdd-guard` for the risky refactor of moving live node implementations and reused the newly added target-tree continuity tests as the pre-move safety net.
- Loaded `docs-update-guard`; the gate applied because the slice materially changed the realized developer-facing runtime layout inside `workflows/pipelines/workflows/image_prompt_gen/`.
- Added `workflows/tests/image_prompt_gen/test_node_router.py` and expanded `workflows/tests/shared/test_compat_state_and_nodes.py` so the compatibility layer had focused assertions before and after the move.
- Created `workflows/pipelines/workflows/image_prompt_gen/nodes/` and moved `load_templates.py`, `cache_lookup.py`, and `router.py` into that package as the new source-of-truth modules.
- Converted the corresponding `ComicBook/comicbook/nodes/*.py` files into legacy compatibility aliases and updated `pipelines.workflows.image_prompt_gen.graph` to import the moved target-tree nodes directly.
- Updated planning/business/developer repo-reorganization indexes and reran focused target-tree scopes, broader target-tree image regressions, and matching legacy regressions; all green.

### 2026-04-25 — TG2 `generate_images_serial` continuity + move slice

- Re-ran manual `implementation-slice-guard` selection and kept TG2-T6 scoped to one remaining image node with a dedicated legacy regression file and one direct graph importer.
- Loaded `pytest-tdd-guard` for the risky refactor and used a target-tree continuity test plus an expanded compat-identity assertion as the safety net.
- The first compat test rerun failed as expected because `pipelines.workflows.image_prompt_gen.nodes.generate_images_serial` did not exist yet; after the move, the focused target-tree and legacy reruns passed.
- Moved `generate_images_serial.py` into `workflows/pipelines/workflows/image_prompt_gen/nodes/`, converted the legacy file into a compatibility alias, updated the image graph import, and refreshed the repo-reorganization triad indexes.

### 2026-04-25 — TG2 remaining image-node move slices

- Re-ran manual `implementation-slice-guard` selection and used the existing target-tree `test_node_ingest_summarize.py` coverage to move `ingest.py` and `summarize.py` together as one inseparable small image-node cluster.
- Added target-tree `test_node_persist_template.py`, used it as the safety net for `persist_template.py`, then moved that final remaining image node into `workflows/pipelines/workflows/image_prompt_gen/nodes/`.
- Updated `pipelines.workflows.image_prompt_gen.graph` so the image workflow now imports its full node set from the target-tree workflow package directly.

### 2026-04-25 — TG2 template-upload node move slices

- Re-ran manual `implementation-slice-guard` selection and first moved the preflight cluster (`upload_load_file.py`, `upload_parse_and_validate.py`, `upload_resume_filter.py`, `upload_decide_write_mode.py`) because `test_node_preflight.py` already covered that cluster tightly.
- Then moved the remaining upload cluster (`upload_backfill_metadata.py`, `upload_persist.py`, `upload_summarize.py`) using existing target-tree backfill/persist coverage plus the broader template-upload regression suite as the safety net for summary/finalization behavior.
- Updated `pipelines.workflows.template_upload.graph` so the template-upload workflow now imports its full node set from the target-tree workflow package directly.
- Refreshed the repo-reorganization triad indexes to record that TG2-T6 is now complete for both workflows.

### 2026-04-25 — Documentation-only revision (prior session)

- Re-ran `/implementation-doc` against the existing planning doc with stricter quality requirements; produced `implementation-v2.md` next to the preserved original `implementation.md`.
- Updated `.opencode/commands/implementation-doc.md` to mandate verified-baseline inspection, canonical `TG{N}-T{M}` task IDs, fully enumerated file lists, mandatory appendices, runnable exit-criteria checks, per-TaskGroup rollback notes, and auto-versioning for non-empty existing implementation guides.
- Updated `.opencode/agents/docs-writer.md` with the matching implementation-guide rules.
- Updated `.opencode/skills/implementation-handoff-guard/SKILL.md` to require canonical task IDs, single-authoritative-guide pairing, and an explicit permission checkpoint section.
- Updated this handoff to point at `implementation-v2.md` as authoritative, re-mapped prior progress to canonical TG{N}-T{M} IDs, and recorded the documentation-only session.
- No runtime code or test files were changed in this session.

### 2026-04-25 — TG2 adjacent-asset move (TG2-T7)

- Used the previously granted explicit approval for TG2-T7's history-preserving `git mv` requirement and moved `ComicBook/examples/` to `workflows/examples/` plus `ComicBook/DoNotChange/` to `workflows/DoNotChange/`.
- Updated `pipelines.shared.repo_protection`, both repo-protection test suites, and the target-tree example continuity test to use the new asset paths.
- Updated repo-reorganization docs, image-prompt workflow docs, README notes, and pre-commit hook labeling so operator and developer guidance now points at `workflows/examples/` and `workflows/DoNotChange/`.
- Verified the moved asset surface with focused target-tree and legacy pytest scopes; all green.

### 2026-04-25 — TG2 test relocation sweep (TG2-T9)

- Used the newly granted explicit approval for TG2-T9's remaining git move, duplicate-test delete, and `__pycache__` cleanup work.
- Moved the final unique legacy test (`test_router_node.py`) into `workflows/tests/image_prompt_gen/` and updated it to import the target-tree node module directly.
- Folded the remaining unique dotenv-override assertion into `workflows/tests/shared/test_config_and_deps.py`.
- Removed the duplicate legacy `ComicBook/tests/test_*.py` files, deleted the now-empty `ComicBook/tests/` directory, and cleaned approved cache artifacts.
- Verified the focused moved/updated tests plus the broad target-tree shared/image/template-upload regression scope; all green.

### 2026-04-25 — TG2 closeout session (TG2-T10 through TG2-T13)

- Completed the image-workflow doc-slug normalization follow-through and verified the legacy mixed-case slug no longer appears in repository docs or agent-facing text.
- Completed the tooling-reference sweep for `AGENTS.md` and the affected `.opencode/agents/*.md` files, leaving only intentional transitional `ComicBook/` references in place.
- Ran the full target-tree pytest exit-gate sequence from `workflows/`: `tests/shared`, `tests/image_prompt_gen`, `tests/template_upload`, and full `pytest -q`; all green (`165 passed` overall).
- Ran target-root CLI help smoke checks for both moved workflow entry points.
- Updated the repo-reorganization triad docs, `workflows/README.md`, and this handoff to mark TG2 complete and point the next session at TG3.

### 2026-04-25 — TG3 state split session (TG3-T1 through TG3-T8)

- Manually re-applied the checked-in `implementation-slice-guard` rules and selected TG3 as the next eligible guide-ordered TaskGroup; kept the whole TaskGroup together because every remaining item was one tightly related contract split with one verification plan.
- Loaded `pytest-tdd-guard` for the risky Python refactor and added state-ownership plus boundary tests before completing the importer rewires.
- Loaded `docs-update-guard`; the gate applied because TG3 changes repository-wide state ownership, compatibility-wrapper behavior, and maintainer-facing module contracts.
- Added the three final authoritative state modules under `workflows/pipelines/shared/`, `workflows/pipelines/workflows/image_prompt_gen/`, and `workflows/pipelines/workflows/template_upload/`.
- Rewired workflow graphs, nodes, prompts, adapters, shared helpers, examples, and tests away from `comicbook.state` and toward the correct split module.
- Replaced both compatibility `state.py` files with explicit re-export wrappers and removed the temporary shared-module legacy-state fallbacks in `db.py`, `fingerprint.py`, and `execution.py`.
- Added `workflows/tests/shared/test_state_modules.py` and `workflows/tests/shared/test_state_boundaries.py`, then ran focused, broader, and full target-tree pytest scopes; all green (`171 passed` overall on the final run).
- Updated the repo-reorganization planning/developer docs and this handoff to mark TG3 complete and point the next session at TG4 logging adoption.

### 2026-04-26 — TG4 logging-adoption slice (TG4-T1, TG4-T2, TG4-T5, TG4-T6, TG4-T7)

- Re-applied the checked-in `implementation-slice-guard` rules and selected the smallest next TG4 slice that stayed inside current approval gates: logging adoption and verification, stopping before the rename half of TG4.
- Loaded `pytest-tdd-guard` for the runtime observability change and added focused workflow logging tests before broad regression reruns.
- Loaded `docs-update-guard`; the gate applied because this slice materially changes runtime observability and operator/developer debugging expectations.
- Added reusable workflow-local node instrumentation decorators and wrapped every runtime node entry point, including the graph-local helper nodes.
- Added focused graph logging tests for both workflows, including successful end-to-end runs and targeted failing-node cases that assert `node_failed` error fields.
- Ran focused log scopes, broader shared/workflow regression, and the full target-tree pytest suite; all green (`175 passed` overall on the final run).
- Updated the planning/business/developer repo-reorganization docs and this handoff to record that TG4 logging adoption is complete and the rename slice remains next.

### 2026-04-26 — TG4 rename/wrapper closeout slice (TG4-T3, TG4-T4, TG4-T8)

- Used the newly granted explicit approval for the rename/delete-like file operations required by the template-upload rename slice.
- Renamed the seven template-upload source-of-truth node modules under `workflows/pipelines/workflows/template_upload/nodes/` and renamed their primary callables to the unprefixed runtime names.
- Rewired `workflows/pipelines/workflows/template_upload/graph.py` so graph node names, imports, routes, and edges now use the unprefixed runtime names.
- Replaced both compatibility-wrapper layers with explicit wrappers that re-export the renamed targets while preserving the legacy `upload_*` callable names for straggler callers.
- Updated compatibility/logging tests and reran focused rename coverage, focused TG4 log coverage, broader shared/workflow regression, and full target-tree pytest; all green (`175 passed` overall on the final run).
- Updated the repo-reorganization planning/business/developer docs and this handoff to mark TG4 complete and point the next session at TG5 cleanup.

### 2026-04-26 — TG5 cleanup slice (TG5-T1, TG5-T2, TG5-T3, TG5-T4, partial TG5-T6/TG5-T8, TG5-T7)

- Used the newly granted explicit approval for TG5 delete-heavy cleanup, including compatibility-shim removal and related cleanup deletes.
- Rewired the remaining functional references away from `comicbook.*`, promoted shared Responses and metadata-backfill helpers into `pipelines.shared`, narrowed package discovery to `pipelines*`, and removed both shim trees plus the compat smoke test.
- Updated active workflow docs, repo-structure standards, AGENTS/agent docs, README, repo-reorganization indexes, and ADR-0002 for the post-shim layout.
- Verified syntax with `py_compile`, verified that `workflows/` no longer imports `comicbook`, and confirmed the shim directories are gone.
- Hit a new blocker on the guide-required pytest/CLI exit gate because deleting the old `ComicBook` uv project removed the only available local pytest environment; the replacement `workflows/` environment now needs explicit install/sync approval before final verification can run.

## Permission checkpoint

- The next guide-ordered incomplete work is the blocked remainder of TG5: final verification and final closeout wording.
- No additional approval is required for continued read-only inspection or handoff/documentation edits that do not install packages or mutate remote state.
- Additional approval **is now required** before any package or module installation / dependency sync needed to run pytest from `workflows/`, plus any copy, `git push`, or remote-mutation work.
- For a future session after this run ends, implementation work should resume only after another explicit `/implement-next-autonomous docs/planning/repo-reorganization/implementation-v2.md docs/planning/repo-reorganization/implementation-handoff.md` approval (or equivalent explicit approval for this autonomous implementation agent). Generic continuation phrases do not count as approval.
