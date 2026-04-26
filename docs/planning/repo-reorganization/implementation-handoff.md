# Implementation Handoff: Repository Reorganization

| Field | Value |
| --- | --- |
| Status | TG1 completed; TG2 completed; TG3 completed; TG4 in progress; TG5 pending |
| Last updated | 2026-04-26 |
| Active implementation guide | `docs/planning/repo-reorganization/implementation-v2.md` |
| Preserved prior guide | `docs/planning/repo-reorganization/implementation.md` (historical; superseded by v2 — kept on disk for traceability of earlier execution) |
| Source plan | `docs/planning/repo-reorganization/plan.md` |
| Planning index | `docs/planning/repo-reorganization/index.md` |
| Business doc | `docs/business/repo-reorganization/index.md` |
| Developer doc | `docs/developer/repo-reorganization/index.md` |
| ADR | `docs/planning/adr/ADR-0002-repo-reorganization.md` (status: **Accepted**, set when TG1 landed) |

> The `/implementation-doc` command was re-run on 2026-04-25 with stricter quality requirements; the resulting `implementation-v2.md` is now authoritative. Going forward, every slice references the canonical task IDs from v2 (`TG{N}-T{M}`). Previously completed work is mapped to those IDs in the table below so no execution detail is lost.

## Current status summary

The shared logging foundation landed under TG1 and has remained stable. TG2 is complete and remains green. TG3 is complete and remains green. TG4 has now started with a logging-adoption slice: reusable instrumentation decorators wrap every image-workflow node, every template-upload node, and the graph-local helper nodes `runtime_gate` and `prepare_deferred_retry`; representative successful runs and targeted failing-node tests now prove that node lifecycle records emit as parseable JSON with `workflow`, `run_id`, `event`, and `node`; and the shared workflow regression plus full target-tree pytest suite still pass from `workflows/`.

What is **not yet** done overall: TG4 still must rename the template-upload `upload_*` modules/functions and update the compatibility wrappers; TG5 still must remove the compatibility shim and finish cleanup. The main remaining temporary fallback noted after this slice is the legacy pricing-path fallback in `pipelines.shared.runtime_deps`, which belongs to later cleanup work.

## TaskGroup progress table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Shared logging foundation | completed | `workflows/pipelines/shared/logging.py` matches the standard; covered by `workflows/tests/shared/test_logging.py`. ADR-0002 set to **Accepted**. |
| TG2 | Move package + tests into `workflows/`, add `comicbook` shim, normalize doc slugs, adopt non-node logging | completed | TG2-T1 through TG2-T13 are complete. Full target-tree pytest exit gate passed; docs gate closed. |
| TG3 | Split state modules | completed | TG3-T1 through TG3-T8 are complete. State ownership is split cleanly and boundary tests plus full pytest passed. |
| TG4 | Adopt node logging + remove `upload_` prefix | in progress | TG4-T1, TG4-T2, TG4-T5, TG4-T6, and representative-run verification for TG4-T7 are complete; the template-upload rename/wrapper slice remains. |
| TG5 | Remove the `comicbook` shim and close the migration | not started | Blocked on TG4. |

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
| TG4-T3 — rename template-upload nodes | pending | Not started in this slice because rename/delete-like file operations remain approval-sensitive under the current session rules. |
| TG4-T4 — update `comicbook/nodes/upload_*.py` wrappers | pending | Blocked on TG4-T3 rename targets. |
| TG4-T5 — add focused logging tests | completed | Added `workflows/tests/image_prompt_gen/test_graph_logging.py` and `workflows/tests/template_upload/test_graph_logging.py` for representative successful runs plus targeted failing-node logging cases. |
| TG4-T6 — run tests in layers | completed | `-k log`, shared+workflow regression, and full `pytest -q` all passed from `workflows/`; final suite stayed green at `175 passed`. |
| TG4-T7 — capture representative sample run output | completed | The new logging tests execute representative end-to-end runs, capture real stdout JSON logs, parse them, and assert the required fields for both workflows. |
| TG4-T8 — documentation gate | in progress | Planning/business/developer repo-reorganization docs and this handoff now record the logging-adoption slice; the final TG4 doc close still depends on the pending rename slice. |

## Last completed slices

### Selected TaskGroup and slices

- **TaskGroup:** TG4
- **Slice cluster:** TG4-T1, TG4-T2, TG4-T5, TG4-T6, and representative-run verification for TG4-T7 as one logging-adoption session
- **Canonical IDs under v2:** TG4-T1, TG4-T2, TG4-T5, TG4-T6, and TG4-T7

### Why these slice boundaries were chosen

TG4 was the next guide-ordered TaskGroup, but the rename half of TG4 (`TG4-T3` and `TG4-T4`) is approval-sensitive because it involves delete-like file-rename work. The smallest meaningful slice that still shipped a useful increment was therefore the logging-adoption cluster: instrument all nodes, add focused log-shape tests, run the guide-layered pytest scopes, and verify representative end-to-end log output before stopping at the rename gate.

### Completed work from this session

- Added reusable workflow-local node instrumentation decorators in `workflows/pipelines/workflows/image_prompt_gen/nodes/__init__.py` and `workflows/pipelines/workflows/template_upload/nodes/__init__.py`.
- Wrapped every image-workflow node, every template-upload node, and the graph-local helper nodes `runtime_gate` and `prepare_deferred_retry` so they emit `node_started`, `node_completed`, and `node_failed` through `log_node_event(...)`.
- Standardized failure logging so node exceptions now emit promoted `error.code`, `error.message`, and `error.retryable` fields plus `duration_ms`.
- Added focused end-to-end logging coverage in `workflows/tests/image_prompt_gen/test_graph_logging.py` and `workflows/tests/template_upload/test_graph_logging.py`.
- Verified that representative successful runs and targeted failing-node cases produce parseable JSON node records with the required standard fields.
- Updated the repo-reorganization planning/business/developer docs and this handoff to record that TG4 logging adoption is landed and the rename slice remains next.

## Files changed in this session

- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`
- `docs/planning/repo-reorganization/index.md`
- `workflows/pipelines/workflows/image_prompt_gen/graph.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/__init__.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/cache_lookup.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/generate_images_serial.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/ingest.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/load_templates.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/persist_template.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/router.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/summarize.py`
- `workflows/pipelines/workflows/template_upload/graph.py`
- `workflows/pipelines/workflows/template_upload/nodes/__init__.py`
- `workflows/pipelines/workflows/template_upload/nodes/upload_backfill_metadata.py`
- `workflows/pipelines/workflows/template_upload/nodes/upload_decide_write_mode.py`
- `workflows/pipelines/workflows/template_upload/nodes/upload_load_file.py`
- `workflows/pipelines/workflows/template_upload/nodes/upload_parse_and_validate.py`
- `workflows/pipelines/workflows/template_upload/nodes/upload_persist.py`
- `workflows/pipelines/workflows/template_upload/nodes/upload_resume_filter.py`
- `workflows/pipelines/workflows/template_upload/nodes/upload_summarize.py`
- `workflows/tests/image_prompt_gen/test_graph_logging.py`
- `workflows/tests/template_upload/test_graph_logging.py`

## Tests run and results

Focused logging-shape scope from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen/test_graph_logging.py tests/template_upload/test_graph_logging.py
```

Result: `4 passed in 0.45s`.

Guide-ordered TG4 logging scope from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload tests/image_prompt_gen -k log
```

Result: `10 passed, 97 deselected in 0.48s`.

Broader regression scope from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared tests/image_prompt_gen tests/template_upload
```

Result: `175 passed in 5.47s`.

Full target-tree suite from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q
```

Result: `175 passed in 5.46s`.

Representative-run log verification:

- `workflows/tests/image_prompt_gen/test_graph_logging.py` executes a successful `run_workflow(...)`, captures stdout JSON log lines, parses them, and asserts `workflow=image_prompt_gen`, a stable `run_id`, `event`, and `node` on node records.
- `workflows/tests/template_upload/test_graph_logging.py` does the same for a successful `run_upload_workflow(...)` with `workflow=template_upload`.
- Both files also include a targeted failing-node case that proves `node_failed` records carry promoted `error.code` fields.

Runtime grep verification:

- `grep` for `deps.logger.*` under `workflows/pipelines/workflows/` → no matches
- `grep` for `logging.getLogger` under `workflows/pipelines/workflows/` → no matches

## Documentation updated

- The docs-update gate applied because this slice materially changed runtime observability behavior and operator/developer expectations around structured workflow logs.
- Updated `docs/planning/repo-reorganization/index.md` to mark TG4 logging adoption in progress and call out the remaining rename slice.
- Updated `docs/business/repo-reorganization/index.md` to explain that operators now get node-level structured lifecycle records while commands remain unchanged.
- Updated `docs/developer/repo-reorganization/index.md` with the decorator-based node instrumentation approach, focused logging tests, and the remaining rename boundary.
- Updated this handoff ledger to record the completed logging-adoption slice and the approval-sensitive next step.
- No ADR or logging standard update was needed because the implementation follows the existing approved logging contract without introducing new fields.

## Blockers or open questions

- The local `implementation-slice-guard` skill exists on disk at `.opencode/skills/implementation-slice-guard/SKILL.md` but is still not loadable through the skill tool, so slice selection continues to apply the checked-in rules manually.
- Direct `pytest` is still unavailable in the shell environment; verification continues to use the locked `ComicBook` uv project with `--no-sync`.
- The pytest runs continue to regenerate tracked and untracked `__pycache__/` artifacts under `workflows/`; deleting those cache files still requires explicit approval because it is a delete operation.
- `pipelines.shared.runtime_deps` still keeps the legacy `ComicBook/comicbook/pricing.json` path as a fallback; that cleanup belongs to later migration work.
- The next TG4 slice is the template-upload rename/wrapper rewrite (`TG4-T3` and `TG4-T4`). Under the current session rules, rename/delete-like file operations are approval-sensitive, so this run stops before that step.
- No technical blocker remains from the logging-adoption slice itself.

## Exact next recommended slice

**Recommended TaskGroup:** TG4.

**Recommended task focus:** complete TG4-T3 and TG4-T4 together as one rename slice: rename the seven template-upload `upload_*` node modules/functions to their unprefixed names, update `workflows/pipelines/workflows/template_upload/graph.py`, and update the `workflows/comicbook/nodes/upload_*.py` wrappers so legacy import paths still re-export the renamed targets.

**Why this slice:**

- TG4 logging adoption is complete and green.
- The rename/wrapper work is the next guide-ordered incomplete TG4 dependency.
- Finishing the rename is the prerequisite for closing TG4 documentation and moving on to TG5 cleanup.

**Boundaries for the next session:**

- keep the work focused on the seven template-upload node renames plus direct importer/wrapper/test updates;
- do not start TG5 cleanup early;
- do not remove compatibility wrappers yet;
- secure explicit approval first if the next session will perform rename/delete-like file operations.

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

## Permission checkpoint

- The next guide-ordered incomplete work is the TG4 template-upload rename/wrapper slice (`TG4-T3` and `TG4-T4`).
- No additional approval would be required only for continued non-destructive read/test/edit work that avoids rename/delete-like operations.
- Additional approval **is still required** before any install, copy, delete (including cleanup of regenerated `__pycache__/` artifacts), `git push`, remote-mutation work, compatibility-wrapper removal, or any rename/delete-like file operation the next session may use for TG4.T3/TG5.
- For a future session after this run ends, implementation work should resume only after another explicit `/implement-next-autonomous docs/planning/repo-reorganization/implementation-v2.md docs/planning/repo-reorganization/implementation-handoff.md` approval (or equivalent explicit approval for this autonomous implementation agent). Generic continuation phrases do not count as approval.
