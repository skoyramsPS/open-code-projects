# Implementation Handoff: Repository Reorganization

| Field | Value |
| --- | --- |
| Status | TG1 completed; TG2 in progress (TG2-T1 through TG2-T9 complete; TG2-T10 next and approval-gated); TG3–TG5 pending |
| Last updated | 2026-04-25 |
| Active implementation guide | `docs/planning/repo-reorganization/implementation-v2.md` |
| Preserved prior guide | `docs/planning/repo-reorganization/implementation.md` (historical; superseded by v2 — kept on disk for traceability of earlier execution) |
| Source plan | `docs/planning/repo-reorganization/plan.md` |
| Planning index | `docs/planning/repo-reorganization/index.md` |
| Business doc | `docs/business/repo-reorganization/index.md` |
| Developer doc | `docs/developer/repo-reorganization/index.md` |
| ADR | `docs/planning/adr/ADR-0002-repo-reorganization.md` (status: **Accepted**, set when TG1 landed) |

> The `/implementation-doc` command was re-run on 2026-04-25 with stricter quality requirements; the resulting `implementation-v2.md` is now authoritative. Going forward, every slice references the canonical task IDs from v2 (`TG{N}-T{M}`). Previously completed work is mapped to those IDs in the table below so no execution detail is lost.

## Current status summary

The shared logging foundation landed under TG1 and has remained stable. TG2 has now completed its bootstrap, shared-module moves, workflow entry-point and graph moves, image-helper moves, mechanical node moves, adjacent-asset moves, explicitly named non-node structured-logging adoption work, and the target-tree test relocation sweep. The target-tree project metadata is in place (`workflows/pyproject.toml`, `workflows/.env.example`); the seven shared infrastructure modules now live in `pipelines.shared.*`; both workflow entry points and graph modules now live under `pipelines.workflows.*`; the image-workflow helpers (input file support, router/metadata prompts, router/image client adapters, pricing asset) have moved into `pipelines.workflows.image_prompt_gen.*`; explicit `workflows/comicbook/state.py` and `workflows/comicbook/nodes/` wrappers replace the prior `__path__`-based fallback; **all workflow node implementations now live under the target-tree workflow packages** (`pipelines.workflows.image_prompt_gen.nodes` and `pipelines.workflows.template_upload.nodes`) while legacy imports still resolve through compatibility aliases; the adjacent shared assets now live at `workflows/examples/` and `workflows/DoNotChange/`; and the canonical pytest tree now lives under `workflows/tests/` with the duplicate legacy `ComicBook/tests/` regression files removed.

What is **not yet** done in TG2: the doc-slug normalization (`Image-prompt-gen-workflow` → `image-prompt-gen-workflow`) has not happened; `pipelines.shared.execution`, `pipelines.shared.fingerprint`, `pipelines.shared.db`, and `pipelines.shared.runtime_deps` still carry temporary fallbacks to legacy modules until TG3 splits state and TG2 cleanup retires the legacy paths; the full target-tree `pytest -q` closeout run has not yet been executed as the TG2 exit gate; and the final TG2 documentation closeout sweep is still pending.

## TaskGroup progress table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Shared logging foundation | completed | `workflows/pipelines/shared/logging.py` matches the standard; covered by `workflows/tests/shared/test_logging.py`. ADR-0002 set to **Accepted**. |
| TG2 | Move package + tests into `workflows/`, add `comicbook` shim, normalize doc slugs, adopt non-node logging | in progress | TG2-T1 through TG2-T9 are complete. TG2-T10, TG2-T11, TG2-T12, and TG2-T13 remain as the ordered TG2 closeout slices. |
| TG3 | Split state modules | not started | Blocked on TG2 completion. |
| TG4 | Adopt node logging + remove `upload_` prefix | not started | Blocked on TG3. |
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
| TG2-T10 — normalize doc-tree slugs | not started | `docs/planning/Image-prompt-gen-workflow/` still uses mixed case. |
| TG2-T11 — update tooling references | not started | Pending end-of-TG2 sweep; `.pre-commit-config.yaml` hook labeling was updated opportunistically during TG2-T7, but the standalone tooling-reference sweep is still pending. |
| TG2-T12 — run full target-tree test suite | not started | `pytest -q` from `workflows/` has not yet been run as a TG2 exit gate; focused subtree scopes pass. |
| TG2-T13 — TG2 documentation gate | not started | Triad pages are updated incrementally per slice but the full TG2 close-out gate has not yet been executed. |

## Last completed slices

### Selected TaskGroup and slices

- **TaskGroup:** TG2
- **Slice cluster:** TG2-T9 remaining test relocation and cleanup sweep
- **Canonical IDs under v2:** TG2-T9, with the minimum direct test/doc cleanups required by the completed move

### Why these slice boundaries were chosen

After TG2-T7 and the already-satisfied TG2-T8 logging work, TG2-T9 was the next incomplete guide-ordered slice. The user then explicitly approved the required history-preserving git move work, duplicate legacy-test deletions, and `__pycache__` cleanup needed for this slice. I kept the work bounded to the remaining pytest-tree migration: move the last unique legacy test into `workflows/tests/`, fold any remaining unique assertion into an existing target-tree test file, remove verified duplicate legacy tests, clean test artifacts, and update migration-facing docs. I did not start TG2-T10 slug normalization or any later TG2 closeout sweep.

### Completed work from this session

- Moved the final unique legacy regression file into the target tree: `ComicBook/tests/test_router_node.py` → `workflows/tests/image_prompt_gen/test_router_node.py`.
- Updated that moved router-node test to import the target-tree node module directly while keeping the current compat-state pattern for shared state types.
- Folded the remaining unique shared-config assertion (`environment overrides dotenv`) into `workflows/tests/shared/test_config_and_deps.py`.
- Removed the duplicate legacy `ComicBook/tests/test_*.py` files after verifying that the target-tree suite already covered those behaviors.
- Deleted the now-empty `ComicBook/tests/` directory and cleaned the approved `__pycache__` artifacts created during prior and current verification.
- Updated migration-facing docs so `workflows/tests/` is now described as the canonical pytest tree and the completed TG2-T9 sweep is recorded.

## Files changed in this session

- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`
- `workflows/README.md`
- `workflows/tests/image_prompt_gen/test_router_node.py`
- `workflows/tests/shared/test_config_and_deps.py`
- removed duplicate legacy test files under `ComicBook/tests/`:
  - `test_budget_guard.py`
  - `test_config.py`
  - `test_db.py`
  - `test_example_single_portrait.py`
  - `test_fingerprint.py`
  - `test_graph_cache_hit.py`
  - `test_graph_happy.py`
  - `test_graph_new_template.py`
  - `test_graph_resume.py`
  - `test_image_client.py`
  - `test_input_file_support.py`
  - `test_node_cache_lookup.py`
  - `test_node_generate_images_serial.py`
  - `test_node_ingest_summarize.py`
  - `test_node_load_templates.py`
  - `test_repo_protection.py`
  - `test_router_validation.py`
  - `test_upload_backfill_metadata.py`
  - `test_upload_decide_write_mode.py`
  - `test_upload_graph.py`
  - `test_upload_load_file.py`
  - `test_upload_parse_and_validate.py`
  - `test_upload_persist.py`
  - `test_upload_resume_filter.py`
  - `test_upload_run_cli.py`
- removed artifact directories:
  - `ComicBook/tests/`
  - `__pycache__/` directories under `workflows/` and the former legacy test tree

## Tests run and results

Focused TG2-T9 verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_config_and_deps.py tests/image_prompt_gen/test_router_node.py
```

Result: `7 passed in 0.06s`.

Broader target-tree regression scope run from `workflows/` after the legacy-test removal sweep:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared tests/image_prompt_gen tests/template_upload
```

Result: `165 passed in 5.09s`.

## Documentation updated

- Updated `docs/planning/repo-reorganization/index.md` to record that TG2-T9 is now complete and the canonical test tree lives under `workflows/tests/`.
- Updated `docs/business/repo-reorganization/index.md` and `docs/developer/repo-reorganization/index.md` to describe the completed test-relocation sweep, legacy-test removal, and remaining TG2 closeout work.
- Updated `workflows/README.md` so the migration notes say the canonical pytest tree is now under `workflows/tests/` and the legacy `ComicBook/tests/` regression tree has been retired.
- Updated this handoff (`docs/planning/repo-reorganization/implementation-handoff.md`) to record the completed TG2-T9 work, verification evidence, and the next approval-gated slice.

## Blockers or open questions

- The local `implementation-slice-guard` skill is checked in at `.opencode/skills/implementation-slice-guard/SKILL.md` but is not currently loadable through the skill tool, so slice selection continues to apply the skill rules manually.
- Direct `pytest` is unavailable in the shell environment used for prior slices; verification reuses the locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- Legacy `ComicBook/comicbook/{config,deps,repo_protection,fingerprint,db,execution,runtime_deps}.py` wrappers still mutate `sys.path` to add the sibling `workflows/` directory; this is a temporary bridge, not the long-term compatibility mechanism, and should be retired as part of TG2 cleanup.
- `pipelines.shared.fingerprint` still falls back to legacy state for `RenderedPrompt`; `pipelines.shared.db` still falls back to legacy state for `TemplateSummary`; both are scheduled to clear when TG3 lands.
- `pipelines.shared.execution` still falls back to legacy state and ingest modules; should clean up in a later TG2 or early TG3 slice.
- `pipelines.shared.runtime_deps` still keeps the legacy `ComicBook/comicbook/pricing.json` path as a fallback; should clear during late TG2 cleanup or TG5.
- No blocking test-relocation gaps remain inside TG2-T9; the remaining work is the ordered TG2 closeout sequence.

## Exact next recommended slice

**Recommended TaskGroup:** TG2.

**Recommended task focus:** start TG2-T10 by normalizing the mixed-case image-prompt workflow doc slug directories (`Image-prompt-gen-workflow` → `image-prompt-gen-workflow`) across planning, business, and developer docs, then update the affected links and references.

**Why this slice:**

- TG2-T9 is now complete.
- TG2-T10 is the next incomplete guide-ordered slice.
- The slug normalization has to happen before the end-of-TG2 tooling-reference sweep and final documentation closeout can be considered complete.

**Boundaries for the next session:**

- do not start TG3 or any later TaskGroup;
- do not start shim removal yet (TG5);
- keep the next slice focused on TG2-T10 slug normalization and the minimum link/reference updates it requires;
- do not mix TG2-T11 tooling-reference cleanup or TG2-T12 full-suite closeout into the same slice unless a later approval explicitly expands scope.

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

## Permission checkpoint

- The next guide-ordered incomplete slice is TG2-T10, which requires state-changing `git mv` operations on the mixed-case image-prompt workflow doc directories under `docs/`.
- Additional approval **is required** before any of the following: state-changing git move commands needed to satisfy TG2-T10 slug normalization, any later delete/copy/install operations outside the completed TG2-T9 scope, `git push` or remote-mutation work, removing any compatibility wrapper, or starting TG3 or any later TaskGroup.
- For a future session after this run ends, implementation work should resume only after another explicit `/implement-next-autonomous docs/planning/repo-reorganization/implementation-v2.md docs/planning/repo-reorganization/implementation-handoff.md` approval (or equivalent explicit approval for this autonomous implementation agent). Generic continuation phrases do not count as approval.
