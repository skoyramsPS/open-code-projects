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

The shared logging foundation landed under TG1 and has remained stable. TG2 has executed many of its sub-tasks: the target-tree project metadata is in place (`workflows/pyproject.toml`, `workflows/.env.example`); the seven shared infrastructure modules now live in `pipelines.shared.*`; both workflow entry points and graph modules now live under `pipelines.workflows.*`; the image-workflow helpers (input file support, router/metadata prompts, router/image client adapters, pricing asset) have moved into `pipelines.workflows.image_prompt_gen.*`; explicit `workflows/comicbook/state.py` and `workflows/comicbook/nodes/` wrappers replace the prior `__path__`-based fallback; non-node runtime logging is adopted in `runtime_deps.py` and both run modules; bounded test relocation into `workflows/tests/` has started across shared, image-prompt-gen, and template-upload subtrees.

What is **not yet** done in TG2: the actual node modules still live under `ComicBook/comicbook/nodes/` (only wrappers exist in the target tree); `ComicBook/examples/` and `ComicBook/DoNotChange/` have not moved to `workflows/`; many legacy tests under `ComicBook/tests/` still co-exist with their relocated counterparts; the doc-slug normalization (`Image-prompt-gen-workflow` → `image-prompt-gen-workflow`) has not happened; `pipelines.shared.execution`, `pipelines.shared.fingerprint`, `pipelines.shared.db`, and `pipelines.shared.runtime_deps` still carry temporary fallbacks to legacy modules until TG3 splits state and TG2 cleanup retires the legacy paths.

## TaskGroup progress table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Shared logging foundation | completed | `workflows/pipelines/shared/logging.py` matches the standard; covered by `workflows/tests/shared/test_logging.py`. ADR-0002 set to **Accepted**. |
| TG2 | Move package + tests into `workflows/`, add `comicbook` shim, normalize doc slugs, adopt non-node logging | in progress | TG2-T1, TG2-T2, TG2-T3, TG2-T4, TG2-T5 complete. TG2-T6 partially complete (target-tree node *wrappers* exist; actual node moves still pending). TG2-T7 not started (examples/DoNotChange not moved). TG2-T8 partially complete (runtime-deps + both run modules use shared logger). TG2-T9 in progress (bounded relocation across shared/image/template-upload subtrees). TG2-T10, TG2-T11, TG2-T12, TG2-T13 not started. |
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
| TG2-T6 — move nodes (mechanical) | partial | Only **wrapper** modules exist under `workflows/comicbook/nodes/` and explicit `workflows/comicbook/state.py`. Actual node implementations still live under `ComicBook/comicbook/nodes/`. Real node moves into `pipelines/workflows/<workflow>/nodes/` are pending. |
| TG2-T7 — move adjacent assets (`examples/`, `DoNotChange/`) | not started | Both still under `ComicBook/`. `pipelines.shared.repo_protection` constants still reference legacy path. |
| TG2-T8 — adopt non-node structured logging | partial | `pipelines.shared.runtime_deps` uses `get_logger("pipelines.run")`; both run modules emit lifecycle events via `log_event(...)`. Other non-node call sites not yet swept. |
| TG2-T9 — relocate tests | in progress | Relocated so far under `workflows/tests/`: `shared/test_logging.py`, `shared/test_runtime_deps.py`, `shared/test_config_and_compat_state.py`, `shared/test_compat_state_and_nodes.py`, `shared/test_fingerprint.py`; `image_prompt_gen/test_graph_scenarios.py`, `support.py`, `test_input_file_support.py`, `test_router_validation.py`, `test_image_client.py`, `test_budget_guard.py`, `test_example_single_portrait.py`, `test_node_ingest_summarize.py`; `template_upload/support.py`, `test_graph_scenarios.py`, `test_run_cli.py`, `test_node_preflight.py`, `test_node_backfill_metadata.py`, `test_node_persist.py`. Many legacy `ComicBook/tests/*` still co-exist (delete operations are approval-gated). |
| TG2-T10 — normalize doc-tree slugs | not started | `docs/planning/Image-prompt-gen-workflow/` still uses mixed case. |
| TG2-T11 — update tooling references | not started | Pending end-of-TG2 sweep; some references already cleaned opportunistically during prior slices. |
| TG2-T12 — run full target-tree test suite | not started | `pytest -q` from `workflows/` has not yet been run as a TG2 exit gate; focused subtree scopes pass. |
| TG2-T13 — TG2 documentation gate | not started | Triad pages are updated incrementally per slice but the full TG2 close-out gate has not yet been executed. |

## Last completed slice

### Selected TaskGroup and slice

- **TaskGroup:** TG2
- **Slice (legacy ID):** bounded template-upload persist node test relocation
- **Canonical ID under v2:** TG2-T9 (test relocation), specifically the upload-persist subset

### Why this slice size was chosen

The first unfinished TaskGroup remained TG2. After the prior bounded shared/image/template-upload/example/fingerprint/node-wrapper/preflight/backfill relocation slices, the next isolated work was the upload-persist continuity coverage. The local `implementation-slice-guard` skill was applied manually (the skill file is checked in but is not currently exposed through the skill tool). Following its rules, this slice was selected because `upload_persist` is one cohesive node with a small fake-db harness, fits one narrow pytest scope, and stays clear of cleanup/deletes, runtime module moves, and TG3 state splitting.

### Completed work from this session

- Added `workflows/tests/template_upload/test_node_persist.py` as target-root coverage for the explicit `comicbook.nodes.upload_persist` wrapper.
- Verified wrapper-backed upload persistence still handles inserted, updated, skipped-duplicate, and failed-validation outcomes correctly from the `workflows/` root.
- Verified wrapper-backed upload persistence still nulls unresolved supersedes targets while preserving the warning in the recorded row result.
- Kept the slice intentionally bounded to the persistence node rather than starting cleanup/delete work or broader upload-node relocation.
- Ran the focused target-tree persist-node scope, the broader target-tree shared/workflow regression scope, and the matching legacy `ComicBook/tests/test_upload_persist.py` scope — all green.

## Files changed in this session

(unchanged from the prior persist-node slice; this handoff revision adds new doc files only)

- `workflows/tests/template_upload/test_node_persist.py`
- `workflows/README.md`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`

In addition, on 2026-04-25 the `/implementation-doc` command was re-run, producing:

- `docs/planning/repo-reorganization/implementation-v2.md` (new authoritative guide)
- updates to `.opencode/commands/implementation-doc.md`, `.opencode/agents/docs-writer.md`, `.opencode/skills/implementation-handoff-guard/SKILL.md` (command/agent/skill quality bar tightened)
- this handoff revision

## Tests run and results

Focused target-tree template-upload persist verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload/test_node_persist.py
```

Result: `5 passed in 0.03s`.

Broader target-tree shared and workflow regression command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared tests/image_prompt_gen tests/template_upload
```

Result: `145 passed in 3.96s`.

Representative legacy template-upload persist regression command run from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_upload_persist.py
```

Result: `5 passed in 0.03s`.

No tests were run during the 2026-04-25 documentation-only session that produced `implementation-v2.md` and the command/agent/skill updates; that session changed planning material only.

## Documentation updated

### Planning

- created `docs/planning/repo-reorganization/implementation-v2.md`
- updated this handoff (`docs/planning/repo-reorganization/implementation-handoff.md`) to point at v2 and re-map prior progress to canonical TG{N}-T{M} IDs
- the prior `docs/planning/repo-reorganization/implementation.md` remains on disk as historical reference; planning index entry should be updated in the next slice to label v2 as current

### Business

- no business-doc changes in the documentation-only session
- prior slice updates to `docs/business/repo-reorganization/index.md` remain in place

### Developer

- no developer-doc changes in the documentation-only session
- prior slice updates to `docs/developer/repo-reorganization/index.md` remain in place

### README / setup docs

- no README changes in the documentation-only session
- `workflows/README.md` retains its prior persist-node slice update

### ADR

- no ADR change in this revision; ADR-0002 remains **Accepted** (set at TG1 close); transitions to **Accepted and Implemented** at TG5.

### Tooling / agents

- updated `.opencode/commands/implementation-doc.md` to mandate verified-baseline inspection, canonical task IDs, full enumerated tables, mandatory appendices, runnable exit criteria, rollback notes per TaskGroup, and auto-versioning for non-empty existing implementation guides
- updated `.opencode/agents/docs-writer.md` with the matching implementation-guide rules
- updated `.opencode/skills/implementation-handoff-guard/SKILL.md` to require the canonical TG{N}-T{M} IDs, explicit pairing with one authoritative implementation guide, and a permission-checkpoint section

## Blockers or open questions

- The local `implementation-slice-guard` skill is checked in at `.opencode/skills/implementation-slice-guard/SKILL.md` but is not currently loadable through the skill tool, so slice selection continues to apply the skill rules manually.
- Direct `pytest` is unavailable in the shell environment used for prior slices; verification reuses the locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- Legacy `ComicBook/comicbook/{config,deps,repo_protection,fingerprint,db,execution,runtime_deps}.py` wrappers still mutate `sys.path` to add the sibling `workflows/` directory; this is a temporary bridge, not the long-term compatibility mechanism, and should be retired as part of TG2 cleanup.
- `pipelines.shared.fingerprint` still falls back to legacy state for `RenderedPrompt`; `pipelines.shared.db` still falls back to legacy state for `TemplateSummary`; both are scheduled to clear when TG3 lands.
- `pipelines.shared.execution` still falls back to legacy state and ingest modules; should clean up in a later TG2 or early TG3 slice.
- `pipelines.shared.runtime_deps` still keeps the legacy `ComicBook/comicbook/pricing.json` path as a fallback; should clear during late TG2 cleanup or TG5.
- Multiple legacy `ComicBook/tests/test_*.py` files remain alongside their relocated counterparts (graph_happy, graph_cache_hit, graph_resume, graph_new_template, input_file_support, router_validation, image_client, upload_graph, upload_run_cli, budget_guard, config, example_single_portrait, fingerprint, node_ingest_summarize, upload_load_file, upload_parse_and_validate, upload_resume_filter, upload_decide_write_mode, upload_backfill_metadata, upload_persist). Delete operations remain approval-gated.
- Running Python verification touched tracked and untracked `__pycache__` artifacts under `workflows/`; left in place because revert/delete cleanup is approval-gated.

## Exact next recommended slice

**Recommended TaskGroup:** TG2.

**Recommended task focus:** continue TG2-T9 (bounded relocation of remaining cross-cutting tests into `workflows/tests/`), or alternatively pick up an early piece of TG2-T6 cleanup that does not require approval-gated deletes (for example, tightening target-tree node-wrapper coverage around still-legacy node modules).

**Why this slice:**

- TG2 is still the first unfinished TaskGroup. After bounded shared, image, template-upload, example, fingerprint, node-wrapper, upload-preflight, upload-backfill, and upload-persist continuity coverage, the remaining safe work is most likely another small wrapper/import-surface or bounded continuity move rather than a large workflow-owned cluster.
- Smaller import-surface or wrapper-coverage slices keep TG2 moving without prematurely mixing in still-legacy node-owned tests or any approval-gated delete cleanup.
- Node-owned tests remain a poor fit for relocation until either runtime ownership moves cleanly or a dedicated slice is chosen to migrate the underlying nodes themselves.

**Boundaries for the next session:**

- do not start TG3 or any later TaskGroup;
- do not move workflow node implementations in the next slice (that is part of TG2-T6 proper, scheduled for a deliberate slice);
- do not remove legacy paths yet (TG5);
- keep the next slice narrowly scoped to one bounded shared/cleanup-oriented test cluster or one bounded wrapper/import-surface improvement.

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

### 2026-04-25 — Documentation-only revision (this session)

- Re-ran `/implementation-doc` against the existing planning doc with stricter quality requirements; produced `implementation-v2.md` next to the preserved original `implementation.md`.
- Updated `.opencode/commands/implementation-doc.md` to mandate verified-baseline inspection, canonical `TG{N}-T{M}` task IDs, fully enumerated file lists, mandatory appendices, runnable exit-criteria checks, per-TaskGroup rollback notes, and auto-versioning for non-empty existing implementation guides.
- Updated `.opencode/agents/docs-writer.md` with the matching implementation-guide rules.
- Updated `.opencode/skills/implementation-handoff-guard/SKILL.md` to require canonical task IDs, single-authoritative-guide pairing, and an explicit permission checkpoint section.
- Updated this handoff to point at `implementation-v2.md` as authoritative, re-mapped prior progress to canonical TG{N}-T{M} IDs, and recorded the documentation-only session.
- No runtime code or test files were changed in this session.

## Permission checkpoint

- The next bounded TG2 test-relocation or wrapper/import-surface slice is pre-approved under `/implement-next-autonomous` per the prior standing approval.
- Additional approval **is required** before any of the following: install/copy/delete operations on legacy `ComicBook/` files, `git push` or remote-mutation work, removing any compatibility wrapper, deleting any legacy test that has a relocated counterpart, starting TG3 or any later TaskGroup, or moving actual node implementations out of `ComicBook/comicbook/nodes/`.
- Implementation work against `implementation-v2.md` may begin only after the user explicitly invokes `/implement-next docs/planning/repo-reorganization/implementation-v2.md docs/planning/repo-reorganization/implementation-handoff.md` (or clearly says `approve /implement-next ...`). Generic continuation phrases do not count as approval.

`USER_APPROVAL_REQUIRED: implementation may start only after explicit /implement-next approval`
