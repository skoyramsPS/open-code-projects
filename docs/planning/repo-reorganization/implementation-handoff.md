# Implementation Handoff: Repository Reorganization

| Field | Value |
| --- | --- |
| Status | TG1 completed; TG2 in progress (substantial slices landed); TG3–TG5 pending |
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

The shared logging foundation landed under TG1 and has remained stable. TG2 has executed many of its sub-tasks: the target-tree project metadata is in place (`workflows/pyproject.toml`, `workflows/.env.example`); the seven shared infrastructure modules now live in `pipelines.shared.*`; both workflow entry points and graph modules now live under `pipelines.workflows.*`; the image-workflow helpers (input file support, router/metadata prompts, router/image client adapters, pricing asset) have moved into `pipelines.workflows.image_prompt_gen.*`; explicit `workflows/comicbook/state.py` and `workflows/comicbook/nodes/` wrappers replace the prior `__path__`-based fallback; non-node runtime logging is adopted in `runtime_deps.py` and both run modules; bounded test relocation into `workflows/tests/` has expanded across shared, image-prompt-gen, and template-upload subtrees; and **all workflow node implementations now live under the target-tree workflow packages** (`pipelines.workflows.image_prompt_gen.nodes` and `pipelines.workflows.template_upload.nodes`) while legacy imports still resolve through compatibility aliases.

What is **not yet** done in TG2: `ComicBook/examples/` and `ComicBook/DoNotChange/` have not moved to `workflows/`; many legacy tests under `ComicBook/tests/` still co-exist with their relocated counterparts; the doc-slug normalization (`Image-prompt-gen-workflow` → `image-prompt-gen-workflow`) has not happened; `pipelines.shared.execution`, `pipelines.shared.fingerprint`, `pipelines.shared.db`, and `pipelines.shared.runtime_deps` still carry temporary fallbacks to legacy modules until TG3 splits state and TG2 cleanup retires the legacy paths.

## TaskGroup progress table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Shared logging foundation | completed | `workflows/pipelines/shared/logging.py` matches the standard; covered by `workflows/tests/shared/test_logging.py`. ADR-0002 set to **Accepted**. |
| TG2 | Move package + tests into `workflows/`, add `comicbook` shim, normalize doc slugs, adopt non-node logging | in progress | TG2-T1, TG2-T2, TG2-T3, TG2-T4, TG2-T5, and TG2-T6 complete. TG2-T7 not started (examples/DoNotChange not moved). TG2-T8 partially complete (runtime-deps + both run modules use shared logger). TG2-T9 in progress (bounded relocation across shared/image/template-upload subtrees). TG2-T10, TG2-T11, TG2-T12, TG2-T13 not started. |
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
| TG2-T7 — move adjacent assets (`examples/`, `DoNotChange/`) | not started | Both still under `ComicBook/`. `pipelines.shared.repo_protection` constants still reference legacy path. |
| TG2-T8 — adopt non-node structured logging | partial | `pipelines.shared.runtime_deps` uses `get_logger("pipelines.run")`; both run modules emit lifecycle events via `log_event(...)`. Other non-node call sites not yet swept. |
| TG2-T9 — relocate tests | in progress | Relocated so far under `workflows/tests/`: `shared/test_logging.py`, `shared/test_runtime_deps.py`, `shared/test_config_and_compat_state.py`, `shared/test_compat_state_and_nodes.py`, `shared/test_fingerprint.py`; `image_prompt_gen/test_graph_scenarios.py`, `support.py`, `test_input_file_support.py`, `test_router_validation.py`, `test_image_client.py`, `test_budget_guard.py`, `test_example_single_portrait.py`, `test_node_ingest_summarize.py`, `test_node_load_templates.py`, `test_node_cache_lookup.py`, `test_node_router.py`, `test_node_generate_images_serial.py`, `test_node_persist_template.py`; `template_upload/support.py`, `test_graph_scenarios.py`, `test_run_cli.py`, `test_node_preflight.py`, `test_node_backfill_metadata.py`, `test_node_persist.py`. Many legacy `ComicBook/tests/*` still co-exist (delete operations are approval-gated). |
| TG2-T10 — normalize doc-tree slugs | not started | `docs/planning/Image-prompt-gen-workflow/` still uses mixed case. |
| TG2-T11 — update tooling references | not started | Pending end-of-TG2 sweep; some references already cleaned opportunistically during prior slices. |
| TG2-T12 — run full target-tree test suite | not started | `pytest -q` from `workflows/` has not yet been run as a TG2 exit gate; focused subtree scopes pass. |
| TG2-T13 — TG2 documentation gate | not started | Triad pages are updated incrementally per slice but the full TG2 close-out gate has not yet been executed. |

## Last completed slices

### Selected TaskGroup and slices

- **TaskGroup:** TG2
- **Slice cluster:** remaining workflow-node migration slices needed to finish TG2-T6, plus the minimum TG2-T9 support needed to keep each move covered
- **Canonical IDs under v2:** TG2-T6 (mechanical node moves) with bounded TG2-T9 support for `generate_images_serial` and `persist_template`

### Why these slice boundaries were chosen

The first unfinished TaskGroup remained TG2. The local `implementation-slice-guard` skill was applied manually before each slice because the skill file is checked in but is not currently exposed through the skill tool. Following its rules, I first took one-node or small-adjacent-node slices where narrow tests already existed (`generate_images_serial`, then `ingest` + `summarize`, then `persist_template`, then the template-upload preflight cluster, then the remaining template-upload backfill/persist/summarize cluster). Those boundaries stayed commit-sized, aligned to existing test seams, and avoided mixing in unrelated asset moves, slug normalization, or TG3 state splitting.

### Completed work from this session

- Added `workflows/tests/image_prompt_gen/test_node_generate_images_serial.py` and `workflows/tests/image_prompt_gen/test_node_persist_template.py` as target-root continuity coverage for the explicit `comicbook.nodes.generate_images_serial` and `comicbook.nodes.persist_template` compatibility surfaces.
- Expanded `workflows/tests/shared/test_compat_state_and_nodes.py` so it now proves moved image-node wrappers (`cache_lookup`, `generate_images_serial`, `ingest`, `load_templates`, `persist_template`, `router`, `summarize`) and moved template-upload wrappers (`upload_load_file`, `upload_parse_and_validate`, `upload_resume_filter`, `upload_backfill_metadata`, `upload_decide_write_mode`, `upload_persist`, `upload_summarize`) resolve to target-tree module objects.
- Observed expected red phases before the new target modules existed: compatibility assertions failed for `generate_images_serial`, then for template-upload moved-node imports, then for `persist_template`.
- Completed the image-workflow node move: `generate_images_serial.py`, `ingest.py`, `persist_template.py`, and `summarize.py` now live under `workflows/pipelines/workflows/image_prompt_gen/nodes/`; the image graph imports all image nodes directly from the target tree.
- Completed the template-upload node move: created `workflows/pipelines/workflows/template_upload/nodes/` and moved `upload_load_file.py`, `upload_parse_and_validate.py`, `upload_resume_filter.py`, `upload_decide_write_mode.py`, `upload_backfill_metadata.py`, `upload_persist.py`, and `upload_summarize.py` into that package; the upload graph imports all upload nodes directly from the target tree.
- Converted the matching `ComicBook/comicbook/nodes/*.py` and `ComicBook/comicbook/nodes/upload_*.py` files into legacy module-alias wrappers to preserve the compatibility surface.
- Updated the planning, business, and developer repo-reorganization index pages so they describe the completed image-node move, completed template-upload node move, and the new continuity coverage.
- Finished TG2-T6 completely without starting TG2-T7 asset moves, delete cleanup, doc-slug normalization, or TG3 state splitting.

## Files changed in this session

- `ComicBook/comicbook/nodes/generate_images_serial.py`
- `ComicBook/comicbook/nodes/ingest.py`
- `ComicBook/comicbook/nodes/persist_template.py`
- `ComicBook/comicbook/nodes/summarize.py`
- `ComicBook/comicbook/nodes/upload_backfill_metadata.py`
- `ComicBook/comicbook/nodes/upload_decide_write_mode.py`
- `ComicBook/comicbook/nodes/upload_load_file.py`
- `ComicBook/comicbook/nodes/upload_parse_and_validate.py`
- `ComicBook/comicbook/nodes/upload_persist.py`
- `ComicBook/comicbook/nodes/upload_resume_filter.py`
- `ComicBook/comicbook/nodes/upload_summarize.py`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`
- `workflows/pipelines/workflows/image_prompt_gen/graph.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/generate_images_serial.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/ingest.py`
- `workflows/pipelines/workflows/image_prompt_gen/nodes/persist_template.py`
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
- `workflows/tests/image_prompt_gen/test_node_generate_images_serial.py`
- `workflows/tests/image_prompt_gen/test_node_persist_template.py`
- `workflows/tests/shared/test_compat_state_and_nodes.py`

## Tests run and results

Focused target-tree image `generate_images_serial` verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen/test_node_generate_images_serial.py
```

Result: `3 passed in 0.50s`.

Focused target-tree image `persist_template` verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen/test_node_persist_template.py
```

Result: `3 passed in 0.39s`.

Focused target-tree image moved-node compatibility + ingest/summarize verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/image_prompt_gen/test_node_ingest_summarize.py
```

Result: `7 passed in 0.38s`.

Focused target-tree moved-node compatibility verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/image_prompt_gen/test_node_generate_images_serial.py
```

Results: first run failed in the expected red phase because `pipelines.workflows.image_prompt_gen.nodes.generate_images_serial` did not exist yet; after the move, the rerun passed with `8 passed in 0.58s`.

Focused target-tree template-upload preflight moved-node verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/template_upload/test_node_preflight.py
```

Result: `20 passed in 0.18s` after the expected red phase where template-upload moved-node imports did not exist yet.

Focused target-tree template-upload backfill/persist moved-node verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/template_upload/test_node_backfill_metadata.py tests/template_upload/test_node_persist.py
```

Result: `17 passed in 0.18s`.

Broader target-tree image-workflow regression command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen
```

Result: `53 passed in 2.54s`.

Broader target-tree template-upload regression command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload
```

Results: `44 passed in 0.90s` and `44 passed in 0.89s` across the upload-node move slices.

Cross-workflow moved-node regression command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/image_prompt_gen tests/template_upload
```

Result: `106 passed in 3.65s`.

Matching legacy image `generate_images_serial` regression command run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_node_generate_images_serial.py
```

Result: `3 passed in 0.45s`.

Matching legacy image ingest/summarize regression command run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_node_ingest_summarize.py
```

Result: `2 passed in 0.27s`.

Matching legacy fingerprint regression command run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_fingerprint.py
```

Result: `9 passed in 0.39s`.

Matching legacy template-upload preflight regressions run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_upload_decide_write_mode.py
```

Result: `14 passed in 0.05s`.

Matching legacy template-upload backfill/persist/graph/run regressions run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_upload_backfill_metadata.py tests/test_upload_persist.py tests/test_upload_graph.py tests/test_upload_run_cli.py
```

Result: `25 passed in 0.89s`.

## Documentation updated

- Updated `docs/planning/repo-reorganization/index.md` to record the completed image-node move and completed template-upload node move.
- Updated `docs/business/repo-reorganization/index.md` to note that operator-visible commands remain stable while both workflows' full node sets now resolve from the target-tree workflow packages.
- Updated `docs/developer/repo-reorganization/index.md` to record the completed target-tree node packages, compatibility aliases, and the additional target-tree continuity coverage.
- Updated this handoff (`docs/planning/repo-reorganization/implementation-handoff.md`) to record the completed TG2-T6 work, verification evidence, and the next approval-gated checkpoint.

## Blockers or open questions

- The local `implementation-slice-guard` skill is checked in at `.opencode/skills/implementation-slice-guard/SKILL.md` but is not currently loadable through the skill tool, so slice selection continues to apply the skill rules manually.
- Direct `pytest` is unavailable in the shell environment used for prior slices; verification reuses the locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- Legacy `ComicBook/comicbook/{config,deps,repo_protection,fingerprint,db,execution,runtime_deps}.py` wrappers still mutate `sys.path` to add the sibling `workflows/` directory; this is a temporary bridge, not the long-term compatibility mechanism, and should be retired as part of TG2 cleanup.
- `pipelines.shared.fingerprint` still falls back to legacy state for `RenderedPrompt`; `pipelines.shared.db` still falls back to legacy state for `TemplateSummary`; both are scheduled to clear when TG3 lands.
- `pipelines.shared.execution` still falls back to legacy state and ingest modules; should clean up in a later TG2 or early TG3 slice.
- `pipelines.shared.runtime_deps` still keeps the legacy `ComicBook/comicbook/pricing.json` path as a fallback; should clear during late TG2 cleanup or TG5.
- Multiple legacy `ComicBook/tests/test_*.py` files remain alongside their relocated counterparts (graph_happy, graph_cache_hit, graph_resume, graph_new_template, input_file_support, router_validation, image_client, router_node, node_load_templates, node_cache_lookup, node_generate_images_serial, fingerprint, node_ingest_summarize, upload_graph, upload_run_cli, upload_load_file, upload_parse_and_validate, upload_resume_filter, upload_decide_write_mode, upload_backfill_metadata, upload_persist, budget_guard, config, example_single_portrait). Delete operations remain approval-gated.
- Running Python verification touched tracked and untracked `__pycache__` artifacts under `workflows/` (including `workflows/pipelines/workflows/image_prompt_gen/__pycache__/graph.cpython-312.pyc` and target-tree test `__pycache__` files); they remain because delete cleanup is approval-gated.

## Exact next recommended slice

**Recommended TaskGroup:** TG2.

**Recommended task focus:** start TG2-T7 by moving `ComicBook/examples/` and `ComicBook/DoNotChange/` into `workflows/`, then update `pipelines.shared.repo_protection` and any path references that still point at the legacy locations.

**Why this slice:**

- TG2-T6 is now complete, so guide order advances to TG2-T7.
- TG2-T7 is the next foundational slice because later cleanup and tooling/doc updates depend on the final asset locations.
- The implementation guide explicitly requires `git mv` for these moves to preserve history, which is the main remaining approval checkpoint.

**Boundaries for the next session:**

- do not start TG3 or any later TaskGroup;
- do not start delete cleanup or shim removal yet (TG5);
- keep the next slice focused on TG2-T7 asset moves and the minimum path-reference updates they require;
- do not mix TG2-T10 slug normalization or TG2-T12 full-suite closeout into the same slice.

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

## Permission checkpoint

- The next guide-ordered slice is TG2-T7, which explicitly calls for `git mv` of `ComicBook/examples` and `ComicBook/DoNotChange` into `workflows/`.
- Additional approval **is required** before any of the following: state-changing git move commands needed to satisfy TG2-T7's history-preserving `git mv` requirement, install/copy/delete operations on legacy `ComicBook/` files, deleting `__pycache__` artifacts, `git push` or remote-mutation work, removing any compatibility wrapper, deleting any legacy test that has a relocated counterpart, or starting TG3 or any later TaskGroup.
- For a future session after this run ends, implementation work should resume only after another explicit `/implement-next-autonomous docs/planning/repo-reorganization/implementation-v2.md docs/planning/repo-reorganization/implementation-handoff.md` approval (or equivalent explicit approval for this autonomous implementation agent). Generic continuation phrases do not count as approval.
