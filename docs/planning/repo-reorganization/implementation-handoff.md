# Implementation Handoff: Repository Reorganization

| Field | Value |
| --- | --- |
| Status | TG1 completed; TG2 completed; TG3 next; TG4–TG5 pending |
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

The shared logging foundation landed under TG1 and has remained stable. TG2 is now complete: the target-tree project metadata is in place (`workflows/pyproject.toml`, `workflows/.env.example`); the seven shared infrastructure modules now live in `pipelines.shared.*`; both workflow entry points and graph modules now live under `pipelines.workflows.*`; the image-workflow helpers (input file support, router/metadata prompts, router/image client adapters, pricing asset) have moved into `pipelines.workflows.image_prompt_gen.*`; explicit `workflows/comicbook/state.py` and `workflows/comicbook/nodes/` wrappers replace the prior `__path__`-based fallback; **all workflow node implementations now live under the target-tree workflow packages** (`pipelines.workflows.image_prompt_gen.nodes` and `pipelines.workflows.template_upload.nodes`) while legacy imports still resolve through compatibility aliases; the adjacent shared assets now live at `workflows/examples/` and `workflows/DoNotChange/`; the canonical pytest tree now lives under `workflows/tests/`; the image-workflow doc slug is normalized across the documentation triad; maintainer/tooling references now treat `workflows/` as canonical; and the full target-tree pytest suite passes from `workflows/`.

What is **not yet** done overall: TG3 must split state ownership into shared and per-workflow modules; TG4 must adopt node-level structured logging and remove the redundant `upload_` prefix; TG5 must remove the compatibility shim and finish cleanup. Temporary fallback logic still remains in `pipelines.shared.execution`, `pipelines.shared.fingerprint`, `pipelines.shared.db`, and `pipelines.shared.runtime_deps` until those later TaskGroups land.

## TaskGroup progress table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Shared logging foundation | completed | `workflows/pipelines/shared/logging.py` matches the standard; covered by `workflows/tests/shared/test_logging.py`. ADR-0002 set to **Accepted**. |
| TG2 | Move package + tests into `workflows/`, add `comicbook` shim, normalize doc slugs, adopt non-node logging | completed | TG2-T1 through TG2-T13 are complete. Full target-tree pytest exit gate passed; docs gate closed. |
| TG3 | Split state modules | not started | Next guide-ordered TaskGroup. |
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
| TG2-T10 — normalize doc-tree slugs | completed | The image-workflow planning, business, and developer doc folders now use `image-prompt-gen-workflow`; top-level indexes, related planning/docs references, ADR links, and implementation-execution examples were updated; grep for the legacy mixed-case slug is now empty. |
| TG2-T11 — update tooling references | completed | `AGENTS.md`, `.opencode/agents/test-engineer.md`, and `.opencode/agents/langgraph-architect.md` now treat `workflows/` / `workflows/tests/` as canonical while describing `ComicBook/comicbook/` only as transitional compatibility surface; `opencode.json` required no change and `.pre-commit-config.yaml` still intentionally points at the legacy protection script path that remains live during the shim window. |
| TG2-T12 — run full target-tree test suite | completed | `uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared`, `tests/image_prompt_gen`, `tests/template_upload`, and full `pytest -q` all passed from `workflows/`; the full suite finished at `165 passed`. |
| TG2-T13 — TG2 documentation gate | completed | Repo-reorganization planning/business/developer docs plus `workflows/README.md` now describe `workflows/` as the active project root, the `comicbook` shim as transitional, normalized workflow doc slugs, and non-node logging adoption. |

## Last completed slices

### Selected TaskGroup and slices

- **TaskGroup:** TG2
- **Slice cluster:** TG2-T10 through TG2-T13 as one ordered TG2 closeout session
- **Canonical IDs under v2:** TG2-T10, TG2-T11, TG2-T12, and TG2-T13

### Why these slice boundaries were chosen

After TG2-T9, the remaining TG2 work formed one coherent closeout cluster: slug normalization (TG2-T10), tooling-reference cleanup (TG2-T11), the full target-tree test gate (TG2-T12), and the final TG2 documentation gate (TG2-T13). I kept the work ordered by the guide and advanced only after each prior slice was green: first finish the doc-path normalization, then refresh maintainer/tooling guidance, then run the full target-tree pytest sequence, then update the final TG2 docs and handoff once the exit criteria were satisfied.

### Completed work from this session

- Updated every remaining image-workflow doc-path reference to use `image-prompt-gen-workflow` across the documentation indexes, implementation-execution workflow docs, related planning docs, ADR references, and the moved image-workflow implementation/handoff docs.
- Refreshed top-level and section indexes so the image workflow quick links now point at the normalized lowercase slug in all three doc trees.
- Updated the repo-reorganization planning, business, and developer docs to record TG2 closeout progress and completion.
- Updated `AGENTS.md`, `.opencode/agents/test-engineer.md`, and `.opencode/agents/langgraph-architect.md` so new work targets `workflows/` / `workflows/tests/` while legacy `ComicBook/*` references are clearly framed as transitional compatibility context.
- Reviewed `opencode.json` and `.pre-commit-config.yaml`; no path rewrite was needed there because the current entries remain valid during the shim window.
- Ran the full target-tree pytest exit-gate sequence from `workflows/`, including shared, image-workflow, template-upload, and full-suite scopes; all passed.
- Ran help-style smoke checks for both moved CLI entry points through `python3 -m pipelines.workflows.image_prompt_gen.run --help` and `python3 -m pipelines.workflows.template_upload.run --help` under the target root.
- Rewrote `workflows/README.md` so it now documents the active project root, canonical package/test locations, local run commands, and the remaining compatibility boundaries.
- Reconciled this handoff ledger so TG2 is marked complete and TG3 is the next ordered TaskGroup.

## Files changed in this session

- `.opencode/agents/langgraph-architect.md`
- `.opencode/agents/test-engineer.md`
- `AGENTS.md`
- `docs/business/image-prompt-gen-workflow/index.md` (renamed path)
- `docs/business/index.md`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/image-prompt-gen-workflow/index.md` (renamed path)
- `docs/developer/implementation-execution-agent/index.md`
- `docs/developer/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/index.md`
- `docs/planning/adr/ADR-0001-implementation-execution-agent.md`
- `docs/planning/image-prompt-gen-workflow/implementation-handoff.md` (renamed path)
- `docs/planning/image-prompt-gen-workflow/implementation.md` (renamed path)
- `docs/planning/image-prompt-gen-workflow/index.md` (renamed path)
- `docs/planning/image-prompt-gen-workflow/input-file-support-design.md` (renamed path)
- `docs/planning/image-prompt-gen-workflow/plan.md` (renamed path)
- `docs/planning/implementation-execution-agent/index.md`
- `docs/planning/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`
- `docs/planning/repo-reorganization/implementation-v2.md`
- `docs/planning/repo-reorganization/implementation.md`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/plan.md`
- `docs/planning/template-upload-workflow/plan.md`
- `workflows/README.md`

## Tests run and results

TG2-T10 and TG2-T11 were documentation/tooling slices; TG2-T12 then ran the full target-tree verification gate; TG2-T13 updated the final docs after the test gate passed.

Verification command run from the repository root:

```bash
python3 - <<'PY'
from pathlib import Path

needle = "Image" + "-prompt-gen-workflow"
matches = []
for path in Path(".").rglob("*"):
    if not path.is_file():
        continue
    if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    if needle in text:
        matches.append(str(path))

print(matches)
PY
```

Result: `[]`.

Additional focused verification via targeted repository search:

- `grep` across `AGENTS.md`, `.opencode/agents/*.md`, `opencode.json`, and `.pre-commit-config.yaml` confirmed that the remaining `ComicBook/` references are either explicit transitional compatibility notes or the still-live legacy protection-script entry point.

Target-tree pytest exit gate run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q
```

Results:

- `tests/shared` → `62 passed in 2.87s`
- `tests/image_prompt_gen` → `59 passed in 4.20s`
- `tests/template_upload` → `44 passed in 1.54s`
- full suite → `165 passed in 5.09s`

CLI help smoke checks from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync python3 -m pipelines.workflows.image_prompt_gen.run --help
uv run --project "../ComicBook" --no-sync python3 -m pipelines.workflows.template_upload.run --help
```

Result: both commands exited successfully.

## Documentation updated

- The docs-update gate applied because this slice changed developer-facing documentation layout, cross-doc path contracts, and repository indexes.
- Updated `docs/index.md`, `docs/planning/index.md`, `docs/business/index.md`, and `docs/developer/index.md` so the image-workflow links now use the normalized lowercase slug.
- Updated the image-workflow planning/business/developer doc references embedded in the implementation-execution workflow docs, the related ADR, the template-upload planning doc, and the preserved input-file implementation/handoff docs.
- Updated the repo-reorganization planning, business, and developer docs plus this handoff to record that TG2 is now complete.
- Updated maintainer-facing guidance in `AGENTS.md` and `.opencode/agents/*.md` so the active package/test roots match the realized migration state.
- Updated `workflows/README.md` to document the active `workflows/` root, canonical package/test locations, local test commands, and CLI help smoke checks.
- No ADR was added or updated for this slice because the change was a path-normalization follow-through within already-approved documentation structure, not a new architectural decision.

## Blockers or open questions

- The local `implementation-slice-guard` skill is checked in at `.opencode/skills/implementation-slice-guard/SKILL.md` but is not currently loadable through the skill tool, so slice selection continues to apply the skill rules manually.
- Direct `pytest` is unavailable in the shell environment used for prior slices; verification reuses the locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- Legacy `ComicBook/comicbook/{config,deps,repo_protection,fingerprint,db,execution,runtime_deps}.py` wrappers still mutate `sys.path` to add the sibling `workflows/` directory; this is a temporary bridge, not the long-term compatibility mechanism, and should be retired as part of TG2 cleanup.
- `pipelines.shared.fingerprint` still falls back to legacy state for `RenderedPrompt`; `pipelines.shared.db` still falls back to legacy state for `TemplateSummary`; both are scheduled to clear when TG3 lands.
- `pipelines.shared.execution` still falls back to legacy state and ingest modules; should clean up in a later TG2 or early TG3 slice.
- `pipelines.shared.runtime_deps` still keeps the legacy `ComicBook/comicbook/pricing.json` path as a fallback; should clear during late TG2 cleanup or TG5.
- The TG2-T12 pytest run regenerated untracked `__pycache__/` directories under `workflows/`. Cleaning them would be a delete operation and therefore needs explicit approval if the next session wants a fully clean working tree before continuing.
- No code blocker remains for TG2; the next implementation work is TG3.

## Exact next recommended slice

**Recommended TaskGroup:** TG3.

**Recommended task focus:** begin TG3 by creating the final state-module ownership split: `workflows/pipelines/shared/state.py`, `workflows/pipelines/workflows/image_prompt_gen/state.py`, and `workflows/pipelines/workflows/template_upload/state.py`, then start rewiring importers in guide order.

**Why this slice:**

- TG2 is now complete.
- TG3 is the next incomplete guide-ordered TaskGroup.
- The next migration dependency is the state split that removes cross-workflow type duplication and temporary legacy fallbacks.

**Boundaries for the next session:**

- keep the next slice focused on the earliest TG3 state-module work and the minimum direct importer/test updates it requires;
- do not start TG4 or TG5 work early;
- preserve the compatibility surface in `workflows/comicbook/state.py` while TG3 is in progress;
- use focused state tests first, then broaden per the TG3 test plan.

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

## Permission checkpoint

- The next guide-ordered incomplete work is TG3.
- No additional approval is required inside the current autonomous run for TG3 if execution continues immediately.
- Additional approval **is still required** before any install, copy, delete (including cleanup of the regenerated `__pycache__/` directories), `git push`, remote-mutation work, or compatibility-wrapper removal.
- For a future session after this run ends, implementation work should resume only after another explicit `/implement-next-autonomous docs/planning/repo-reorganization/implementation-v2.md docs/planning/repo-reorganization/implementation-handoff.md` approval (or equivalent explicit approval for this autonomous implementation agent). Generic continuation phrases do not count as approval.
