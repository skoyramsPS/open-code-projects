# Technical Implementation Guide: Repository Reorganization

**Status:** Draft for implementation  
**Date:** 2026-04-24  
**Source planning document:** `docs/planning/repo-reorganization/plan.md`  
**Audience:** delivery team  
**Authority:** This is the primary execution document for the repository reorganization. Implementation should not require reopening the source planning document except for historical context.

---

## 1. Purpose and scope

This guide converts the repository reorganization plan into an execution-ready sequence for moving the codebase from the legacy `ComicBook/comicbook/` layout to the target multi-workflow `workflows/pipelines/` layout.

The implementation must deliver these outcomes:

- separate shared infrastructure from workflow-owned code
- make the target `pipelines` package the real runtime package, not just a documented future state
- preserve both existing workflows during the move:
  - image prompt generation
  - template upload
- adopt one shared structured-logging module across workflow and shared runtime code
- keep the repository runnable and testable throughout the migration
- preserve external compatibility long enough to avoid a forced big-bang import break

This guide covers only the code reorganization and its required planning follow-through. It does **not** authorize implementation during this planning command, and it does **not** change runtime code, tests, or non-planning documentation by itself.

This future implementation is **significant** and will require the full documentation gate when code lands. This planning command, however, is a planning-only documentation update, so only planning docs are changed now.

---

## 2. Current repository baseline

Implementation must start from the repository that exists now, not from the cleaner target state described in standards.

### 2.1 Top-level layout today

The repo currently contains both the legacy runtime home and an early target-layout scaffold:

```text
.
├── AGENTS.md
├── ComicBook/
│   ├── comicbook/
│   ├── tests/
│   ├── examples/
│   ├── DoNotChange/
│   ├── pyproject.toml
│   └── .env.example
├── docs/
└── workflows/
    ├── README.md
    └── pipelines/
        ├── __init__.py
        ├── shared/
        │   ├── __init__.py
        │   └── logging.py
        └── workflows/
            └── __init__.py
```

### 2.2 Legacy runtime reality

The working code still lives under `ComicBook/comicbook/`.

Current legacy package contents include:

- shared runtime modules: `config.py`, `db.py`, `deps.py`, `execution.py`, `fingerprint.py`, `repo_protection.py`, `runtime_deps.py`, `state.py`
- image workflow modules: `graph.py`, `run.py`, `input_file.py`, `router_llm.py`, `router_prompts.py`, `metadata_prompts.py`, `image_client.py`, `nodes/*`
- template upload workflow modules: `upload_graph.py`, `upload_run.py`, `nodes/upload_*`

Current tests also remain in the legacy tree under `ComicBook/tests/`, and they import the legacy `comicbook` package directly.

### 2.3 Target-layout assets that already exist

The target tree is not empty. These assets already exist under `workflows/`:

- `workflows/README.md`
- `workflows/pipelines/__init__.py`
- `workflows/pipelines/workflows/__init__.py`
- `workflows/pipelines/shared/logging.py`

The logging module is therefore **not** a purely hypothetical future artifact. Implementation must treat it as the starting point for the migration, then adjust it as needed to match the final standard and tests.

### 2.4 Logging adoption gap today

Despite the presence of `workflows/pipelines/shared/logging.py`, runtime adoption has not happened yet:

- `ComicBook/comicbook/runtime_deps.py` still constructs `logging.getLogger("comicbook.run")`
- `ComicBook/comicbook/run.py` still emits plain `logger.info(...)` and `logger.exception(...)` calls
- no legacy runtime module currently imports `pipelines.shared.logging`
- there are no dedicated tests for the shared logging module

### 2.5 Packaging and test reality today

Current packaging and test constraints:

- `ComicBook/pyproject.toml` still defines the project around the `comicbook` package
- package discovery includes only `comicbook*`
- `pytest` is configured from `ComicBook/pyproject.toml`
- there is no `workflows/pyproject.toml`
- there is no `workflows/tests/` tree yet

### 2.6 Stable boundaries this migration must preserve

Unless a TaskGroup explicitly says otherwise, preserve these behaviors during implementation:

- both workflows must remain executable throughout the migration
- the SQLite schema and workflow persistence semantics must remain behaviorally compatible
- `DoNotChange/` content remains protected and outside the Python package
- no new third-party logging package is introduced
- tests continue to run with `pytest`
- migration should preserve git history where files are moved, using `git mv`

---

## 3. Resolved ambiguities and locked decisions

The planning document leaves several implementation details underspecified or inconsistent with the current repo. The decisions below are locked for execution.

### 3.1 The top-level move is an in-place convergence, not a literal folder rename

The plan describes `ComicBook/` → `workflows/`, but `workflows/` already exists and already contains the target package scaffold.

**Decision:** treat the migration as a convergence into the existing `workflows/` tree.

Practical meaning:

- expand `workflows/` until it becomes the primary project root for runtime code and tests
- move source-controlled assets out of `ComicBook/` into `workflows/`
- remove or retire legacy paths only after their replacements are green
- do not try to perform a single filesystem rename from `ComicBook/` to `workflows/`

### 3.2 Phase 1 cannot wire legacy runtime code directly to `pipelines.shared.logging`

The plan says Phase 1 should wire `runtime_deps.py` and CLI entry points to the new shared logger while package locations remain unchanged. In the current repo, that is not cleanly importable because `pipelines` lives under the sibling `workflows/` directory and is not part of the installed `comicbook` package.

**Decision:** split the work this way:

- **TG1** finalizes and tests `workflows/pipelines/shared/logging.py` in the target tree
- runtime adoption of that module moves to **TG2**, when code is actually moved into `workflows/` and `pipelines` becomes importable as the real runtime package

Why:

- avoids sys.path hacks or duplicate logger implementations
- preserves the single-source-of-truth rule for logging
- keeps TG1 valuable without introducing packaging debt that TG2 would immediately undo

### 3.3 Compatibility is a full temporary package, not only `comicbook/__init__.py`

The plan suggests a `comicbook/__init__.py` shim or an editable-install alias. Current tests and likely external scripts import many legacy submodules such as:

- `comicbook.graph`
- `comicbook.run`
- `comicbook.upload_run`
- `comicbook.db`
- `comicbook.nodes.upload_load_file`

**Decision:** Phase 2 creates a temporary `workflows/comicbook/` compatibility package with explicit wrapper modules and a `nodes/` wrapper subpackage.

Do **not** rely on:

- a single `__init__.py` re-export
- `sys.path` mutation
- dynamic `sys.modules` tricks as the primary compatibility mechanism

Explicit wrappers are easier to test, easier to delete in TG5, and clearer for maintainers.

### 3.4 Distribution metadata stays conservative during the shim window

The plan renames the import package to `pipelines`, but it does not require an immediate distribution-package rename.

**Decision:** when `pyproject.toml` moves under `workflows/`, keep packaging conservative during the compatibility window:

- make `pipelines*` the real code packages
- include `comicbook*` wrapper packages while the shim exists
- a distribution-name rename is **not required** for this migration and should be deferred unless a release need forces it

This reduces installer churn while the import transition is still active.

### 3.5 Existing `COMICBOOK_*` runtime env vars remain in scope during the migration

The plan requires path updates and a new logging standard, but it does not require a repository-wide env-var rename.

**Decision:** keep the current `COMICBOOK_*` configuration variables for runtime behavior across TG1-TG5.

Only the new logging controls remain under the standard-defined names:

- `PIPELINES_LOG_FORMAT`
- `PIPELINES_LOG_LEVEL`

Reason: changing package layout and config names in one migration would create unnecessary operator-facing breakage.

### 3.6 Tests move with code in TG2; TG1 uses a narrow target-tree test command

Because `workflows/` is not yet the active package root, TG1 cannot rely on the legacy `ComicBook` pytest configuration.

**Decision:** TG1 adds focused logging tests in the target tree and runs them explicitly with the target tree on `PYTHONPATH`. Example verification command:

```bash
PYTHONPATH=workflows pytest -q workflows/tests/shared/test_logging.py
```

Then TG2 moves or normalizes test layout so the standard `pytest -q` flow from `workflows/` becomes the normal command.

### 3.7 ADR-0002 status progression is resolved in favor of the ADR text

The plan says ADR-0002 is marked Accepted at the end of Phase 5. The ADR itself says it becomes Accepted when implementation starts landing and becomes Accepted and Implemented at the end of Phase 5.

**Decision:** use the ADR wording:

- set ADR-0002 to **Accepted** when TG1 code lands
- set ADR-0002 to **Accepted and Implemented** after TG5 cleanup completes

That makes the ADR status reflect reality during the multi-phase rollout.

### 3.8 No persistence-schema redesign is part of this migration

The migration reorganizes code ownership and logging behavior. It does **not** redesign SQLite tables or workflow data semantics.

**Decision:** any persistence change during these TaskGroups must be strictly mechanical or logging-supporting. Do not introduce unrelated schema features while performing the move.

---

## 4. Target architecture and migration contract

### 4.1 Final target layout

By the end of TG5, the repo should behave as though this is the real runtime structure:

```text
workflows/
├── pyproject.toml
├── .env.example
├── README.md
├── DoNotChange/
├── examples/
├── pipelines/
│   ├── __init__.py
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── deps.py
│   │   ├── execution.py
│   │   ├── fingerprint.py
│   │   ├── logging.py
│   │   ├── repo_protection.py
│   │   ├── runtime_deps.py
│   │   └── state.py
│   └── workflows/
│       ├── __init__.py
│       ├── image_prompt_gen/
│       │   ├── __init__.py
│       │   ├── graph.py
│       │   ├── run.py
│       │   ├── input_file.py
│       │   ├── state.py
│       │   ├── pricing.json
│       │   ├── adapters/
│       │   │   ├── image_client.py
│       │   │   └── router_llm.py
│       │   ├── prompts/
│       │   │   ├── metadata_prompts.py
│       │   │   └── router_prompts.py
│       │   └── nodes/
│       │       ├── cache_lookup.py
│       │       ├── generate_images_serial.py
│       │       ├── ingest.py
│       │       ├── load_templates.py
│       │       ├── persist_template.py
│       │       ├── router.py
│       │       └── summarize.py
│       └── template_upload/
│           ├── __init__.py
│           ├── graph.py
│           ├── run.py
│           ├── state.py
│           └── nodes/
│               ├── backfill_metadata.py
│               ├── decide_write_mode.py
│               ├── load_file.py
│               ├── parse_and_validate.py
│               ├── persist.py
│               ├── resume_filter.py
│               └── summarize.py
├── comicbook/                  # temporary compatibility package, removed in TG5
└── tests/
    ├── shared/
    ├── image_prompt_gen/
    ├── template_upload/
    └── integration/
```

### 4.2 Module ownership rules

Shared modules under `pipelines/shared/` own only cross-workflow concerns:

- config loading
- dependency container and runtime construction
- SQLite access and repo protection
- shared state models used by more than one workflow
- execution helpers
- shared logging

Workflow-owned modules under `pipelines/workflows/<workflow>/` own:

- graph assembly
- workflow entry points
- workflow-only state models
- prompts and adapters that have only one importer
- workflow-specific nodes

Promotion rule:

- if a workflow-local module gains a second importer from another workflow, move it into `pipelines/shared/` in TG5 or in a later follow-up if the second importer appears after this migration

### 4.3 Runtime contracts after migration

The runtime contracts should be:

- image workflow entry points live under `pipelines.workflows.image_prompt_gen.run`
- template upload entry points live under `pipelines.workflows.template_upload.run`
- cross-workflow helpers are imported only from `pipelines.shared.*`
- nodes keep the existing callable shape:

```python
def node_name(state, deps):
    return state_delta
```

- wrapper modules in `workflows/comicbook/` re-export the new homes without introducing new business logic

### 4.4 State and data-model split contract

Final state placement must match these rules.

`pipelines/shared/state.py` contains only cross-workflow types, including:

- `WorkflowModel`
- `WorkflowError`
- `UsageTotals`
- `RunSummary`
- `RunStatus`
- any shared status helpers used by more than one workflow

`pipelines/workflows/image_prompt_gen/state.py` contains image-workflow-only contracts, including:

- `RunState`
- `TemplateSummary`
- `NewTemplateDraft`
- `PromptPlanItem`
- `RouterTemplateDecision`
- `RouterPlan`
- `RenderedPrompt`
- `ImageResult`
- image-workflow-only literals such as `ImageSize`, `ImageQuality`, `RouterModel`, `ImageResultStatus`

`pipelines/workflows/template_upload/state.py` contains template-upload-only contracts, including:

- `ImportRunState`
- `TemplateImportRow`
- `TemplateImportRowResult`
- `ImportRowStatus`
- `ImportWriteMode`

No model may be duplicated across files.

### 4.5 Persistence expectations

Persistence remains on the current SQLite schema and DAO behavior unless a move requires purely mechanical import or module-path updates.

Required expectations:

- `pipelines.shared.db` remains the single home of SQLite access
- run-lock behavior for both workflows must remain intact through the move
- no new database tables are introduced solely because of the reorganization
- state splitting must not change persisted field names, report contents, or row semantics unless explicitly required by logging adoption

### 4.6 Observability contract

The logging standard becomes mandatory by the end of TG4.

Required fields on every structured record:

- `timestamp`
- `level`
- `logger`
- `event`
- `workflow`
- `run_id`
- `message`

Additional required rule for node-context records:

- include `node`

Implementation posture:

- non-node code uses `get_logger(__name__)` plus `log_event(...)`
- nodes use `log_node_event(deps, state, event, **fields)`
- direct `logging.getLogger(...)` and direct `deps.logger.info(...)` inside nodes are considered incomplete once TG4 starts

### 4.7 Failure-handling contract

Across all TaskGroups:

- every phase must end with a runnable, testable repository state
- if a TaskGroup requires temporary compatibility code, that code must be explicitly listed and explicitly removed later
- do not mix unrelated refactors into the move
- use the smallest test scope first, then broaden
- do not delete legacy entry paths until their replacement import paths and compatibility shims are proven by tests

---

## 5. TaskGroup overview

| TaskGroup | Title | Depends on | Primary outcome |
| --- | --- | --- | --- |
| TG1 | Finalize and verify the shared logging foundation | none | `pipelines.shared.logging` is correct and tested in the target tree |
| TG2 | Move package and tests into `workflows/` with compatibility wrappers | TG1 | `pipelines` becomes the real runtime package, legacy `comicbook` imports still work |
| TG3 | Split shared and workflow-specific state modules | TG2 | state ownership matches the target layout with no duplicated models |
| TG4 | Complete structured logging adoption and template-upload naming cleanup | TG3 | all runtime code emits standardized structured logs and template-upload names match the target convention |
| TG5 | Remove compatibility scaffolding and close the migration | TG4 | no legacy path remains, docs and ADR are fully closed out |

TaskGroups are sequential. Do not begin a later TaskGroup until the prior one meets its exit criteria.

---

## 6. TaskGroup details

## TG1 — Finalize and verify the shared logging foundation

### Goal

Make `workflows/pipelines/shared/logging.py` fully match the logging standard and back it with focused automated tests.

### Dependencies

- none

### Detailed tasks

1. Review `workflows/pipelines/shared/logging.py` against `docs/standards/logging-standards.md`.
2. Adjust the module so its public surface and behavior match the standard exactly:
   - `get_logger(name)`
   - `JsonFormatter`
   - `NodeLogContext`
   - `log_event(...)`
   - `log_node_event(...)`
3. Verify formatter behavior for:
   - required fields always present
   - optional promoted fields handled correctly
   - non-promoted extras nested under `extra`
   - exception information serialized consistently
   - default JSON mode and opt-in text mode
4. Add narrow tests under the target tree for formatter and helper behavior.
5. Do **not** yet rewire legacy `ComicBook/comicbook/` runtime imports to the target module.

### Expected files or modules

- `workflows/pipelines/shared/logging.py`
- `workflows/tests/shared/test_logging.py` or a similarly named focused test file under `workflows/tests/shared/`

### Testing and verification

Run the smallest meaningful scope first from the repo root:

```bash
PYTHONPATH=workflows pytest -q workflows/tests/shared/test_logging.py
```

Test expectations:

- `JsonFormatter` asserts required fields
- `log_event(...)` asserts non-node standard fields
- `log_node_event(...)` asserts `workflow`, `run_id`, `node`, and `event`
- duplicate handlers are not added when `get_logger(...)` is called repeatedly

### Exit criteria

- shared logging module behavior matches the standard
- focused logging tests pass
- no legacy runtime module imports the target logger yet
- repository remains unchanged outside the logging foundation and its tests

### Handoff notes for TG2

- TG2 should treat `workflows/pipelines/shared/logging.py` as production-ready infrastructure
- if TG1 reveals a standard/document mismatch, update planning docs before TG2 starts
- ADR-0002 becomes **Accepted** when TG1 code lands

---

## TG2 — Move package and tests into `workflows/` with compatibility wrappers

### Goal

Make `workflows/` the actual runtime root, move modules into the target ownership layout, and keep legacy `comicbook` imports working through explicit wrapper modules.

### Dependencies

- TG1 complete

### Detailed tasks

1. Create `workflows/pyproject.toml` by moving and updating `ComicBook/pyproject.toml`.
2. Move source-controlled assets with `git mv` wherever practical:
   - runtime package files from `ComicBook/comicbook/` into `workflows/pipelines/`
   - tests from `ComicBook/tests/` into `workflows/tests/`
   - `ComicBook/examples/` into `workflows/examples/`
   - `ComicBook/DoNotChange/` into `workflows/DoNotChange/`
   - `ComicBook/.env.example` into `workflows/.env.example`
3. Re-home modules according to the migration mapping, including:
   - shared modules into `pipelines/shared/`
   - image workflow modules into `pipelines/workflows/image_prompt_gen/`
   - template upload modules into `pipelines/workflows/template_upload/`
4. Rewire imports so moved code imports from `pipelines.*`, not from `comicbook.*`.
5. Move runtime-deps and CLI logging adoption into this TaskGroup:
   - `runtime_deps.py` uses `get_logger(...)`
   - CLI and non-node runtime modules use `log_event(...)`
6. Create the temporary compatibility package under `workflows/comicbook/` with explicit wrapper modules for legacy import paths.
7. Create a wrapper `workflows/comicbook/nodes/` package so existing legacy node imports remain functional.
8. Update package discovery so both `pipelines*` and temporary `comicbook*` packages are installed during the compatibility window.
9. Update path-sensitive configuration and helper references:
   - `.env.example`
   - repo-protection path checks
   - pre-commit or tooling references that point to `ComicBook/`
   - documented pytest working directory expectations for the new root
10. Rename the image workflow doc folder slug from `Image-prompt-gen-workflow` to `image-prompt-gen-workflow` across the documentation triad and indexes as part of this TaskGroup's full docs gate.

### Expected files or modules

- `workflows/pyproject.toml`
- `workflows/.env.example`
- `workflows/pipelines/shared/*.py`
- `workflows/pipelines/workflows/image_prompt_gen/**`
- `workflows/pipelines/workflows/template_upload/**`
- `workflows/comicbook/**` temporary wrappers
- `workflows/tests/**`
- any path-dependent helper or config files needed to keep tooling valid

### Testing and verification

Run focused verification first, then the broad suite from `workflows/`:

```bash
pytest -q tests/shared
pytest -q tests/image_prompt_gen tests/template_upload
pytest -q
```

Additional required checks:

- import tests prove both `pipelines.*` and temporary `comicbook.*` paths work
- CLI smoke tests for both workflows work from the new `workflows/` root
- no remaining runtime import depends on `ComicBook/comicbook/` as the source of truth

### Exit criteria

- the real runtime package lives under `workflows/pipelines/`
- tests run from `workflows/`
- temporary `comicbook` wrapper package keeps legacy imports working
- shared logging is actively used by non-node runtime code
- doc-slug normalization for `image-prompt-gen-workflow` is complete

### Handoff notes for TG3

- TG3 must split state only after all imports resolve against the moved package tree
- keep the wrapper package thin; do not add new behavior there
- record any wrapper modules added so TG5 can delete them deterministically

---

## TG3 — Split shared and workflow-specific state modules

### Goal

Move the current mixed `state.py` contents into their final ownership homes without changing workflow behavior.

### Dependencies

- TG2 complete

### Detailed tasks

1. Create `pipelines/shared/state.py` for cross-workflow types.
2. Create `pipelines/workflows/image_prompt_gen/state.py` for image-workflow-only types.
3. Create `pipelines/workflows/template_upload/state.py` for upload-workflow-only types.
4. Move types from the legacy combined state file into those modules according to the locked split contract in Section 4.4.
5. Update every import in:
   - workflow graphs
   - run modules
   - nodes
   - shared helpers
   - tests
   - compatibility wrappers
6. Ensure `__all__` exports remain explicit and stable.
7. Remove duplication and keep shared base types imported from `pipelines.shared.state`.

### Expected files or modules

- `workflows/pipelines/shared/state.py`
- `workflows/pipelines/workflows/image_prompt_gen/state.py`
- `workflows/pipelines/workflows/template_upload/state.py`
- updated imports across the moved package and tests
- updated wrapper modules that still expose the old legacy import surface

### Testing and verification

Run the smallest relevant scopes first, then broaden:

```bash
pytest -q tests/shared tests/image_prompt_gen tests/template_upload -k state
pytest -q tests/image_prompt_gen tests/template_upload
pytest -q
```

Required assertions:

- both workflows still execute with the same state behavior
- no workflow imports another workflow's state module directly
- shared modules import only from `pipelines.shared.state`

### Exit criteria

- mixed legacy state ownership is eliminated from the real `pipelines` package
- no duplicated model definitions remain
- tests pass after import rewiring
- compatibility wrappers still present the legacy state imports correctly

### Handoff notes for TG4

- after TG3, logging adoption can infer workflow-specific state homes cleanly
- if any type still feels cross-workflow but has only one importer, keep it local unless a second importer exists

---

## TG4 — Complete structured logging adoption and template-upload naming cleanup

### Goal

Apply the shared logging contract throughout runtime code and remove redundant `upload_` naming where the directory already establishes workflow scope.

### Dependencies

- TG3 complete

### Detailed tasks

1. Replace direct node-level logging with `log_node_event(...)` across both workflows.
2. Replace non-node runtime logging with `get_logger(...)` and `log_event(...)` where still missing.
3. Ensure every emitted record carries the standard fields:
   - `workflow`
   - `run_id`
   - `event`
   - `node` when inside a node
4. Add or update dedicated logging tests where current tests do not exercise field presence.
5. Rename template-upload modules and functions to remove redundant `upload_` prefixes inside the real `pipelines` package:
   - module examples: `load_file.py`, `parse_and_validate.py`, `resume_filter.py`, `backfill_metadata.py`, `decide_write_mode.py`, `persist.py`, `summarize.py`
   - function names should match the simplified module names
6. Update graph assembly, tests, and compatibility wrappers to match the simplified names.
7. Verify a representative run of each workflow produces auditable structured logs.

### Expected files or modules

- logging call sites across `workflows/pipelines/shared/**`
- logging call sites across both workflow packages
- `workflows/pipelines/workflows/template_upload/nodes/*.py`
- upload graph and run modules
- logging-focused tests under `workflows/tests/**`
- compatibility wrappers for renamed legacy node imports

### Testing and verification

Required verification layers:

```bash
pytest -q tests/template_upload tests/image_prompt_gen -k log
pytest -q tests/shared tests/image_prompt_gen tests/template_upload
pytest -q
```

And one sample execution path per workflow to inspect produced log lines.

Validation requirements:

- node logs include `workflow`, `run_id`, `event`, `node`
- non-node logs include the required standard fields
- no node still relies on direct `deps.logger.*`
- simplified template-upload names are reflected consistently in code and imports

### Exit criteria

- structured logging is standard across runtime code
- template-upload naming matches the target layout
- representative workflow runs produce auditable logs using only standard fields
- tests remain green after naming cleanup

### Handoff notes for TG5

- TG5 may now remove compatibility layers with high confidence because the new names and logging paths are the stable ones
- capture any remaining wrapper-only legacy names that still need removal in TG5

---

## TG5 — Remove compatibility scaffolding and close the migration

### Goal

Finish the reorganization by removing legacy compatibility paths, sweeping stale references, and closing the documentation and ADR work.

### Dependencies

- TG4 complete

### Detailed tasks

1. Delete the temporary `workflows/comicbook/` compatibility package.
2. Remove any remaining references to legacy import paths in:
   - runtime code
   - tests
   - docs
   - agent instructions
   - tooling/config files
3. Confirm no source-controlled runtime code still depends on `ComicBook/comicbook/`.
4. Promote any module that now has more than one workflow importer into `pipelines/shared/`.
5. Run the full documentation gate for the completed migration:
   - planning docs
   - business docs
   - developer docs
   - impacted indexes
6. Update ADR-0002 from **Accepted** to **Accepted and Implemented**.
7. Confirm examples, commands, and path references match the final `workflows/` reality.

### Expected files or modules

- deletion of `workflows/comicbook/**`
- cleanup across `workflows/pipelines/**`
- cleanup across `workflows/tests/**`
- cleanup across `docs/**`
- cleanup across `AGENTS.md`, `.opencode/agents/**`, and relevant standards
- `docs/planning/adr/ADR-0002-repo-reorganization.md`

### Testing and verification

Final verification from `workflows/`:

```bash
pytest -q
```

Plus required grep-based or equivalent verification that no legacy code paths remain.

Required final assertions:

- no import of `comicbook` remains in shipped runtime or test code
- no lingering `ComicBook/` source path remains in docs or agent instructions unless it is explicitly historical context
- both workflows run from `pipelines.*` entry points only

### Exit criteria

- the compatibility package is gone
- the repository reflects the documented target layout in reality
- documentation triad and indexes are synchronized
- ADR-0002 is marked **Accepted and Implemented**
- no lingering legacy runtime path remains outside historical references

### Handoff notes

- once TG5 is complete, this implementation guide should be marked fully executed in the sibling handoff document
- any further structural changes after TG5 should use a new planning update or a follow-up ADR rather than extending the temporary compatibility design

---

## 7. Cross-cutting testing requirements

Across all TaskGroups:

- use pytest-first when practical for Python behavior changes
- prefer the narrowest failing scope first
- broaden only after focused green results
- preserve or improve coverage for imports, runtime entry points, and moved-node behavior
- treat compatibility wrappers as testable surfaces, not unverified glue

Minimum verification sequence per TaskGroup:

1. focused unit or module-scope pytest run for the files touched
2. broader workflow-scope pytest run for affected workflows
3. full `pytest -q` once the TaskGroup is functionally complete

If a TaskGroup changes runtime logging behavior, include at least one log-shape assertion or dedicated logging test.

---

## 8. Cross-cutting documentation and observability requirements

When implementation begins, this reorganization triggers the documentation gate.

Required updates during implementation, not during this planning-only command:

- `docs/planning/` for migration progress, phase completion, and handoff updates
- `docs/business/` for user-facing and operator-facing path/runtime changes
- `docs/developer/` for setup, layout, import, debugging, and extension changes
- impacted `index.md` files at every touched level
- ADR-0002 status updates as described in Section 3.7

Observability requirements during implementation:

- log lines remain machine-parseable JSON by default
- any new node log site honors redaction flags already defined by the workflows
- no phase is complete until operators can identify `workflow`, `run_id`, and node context from logs where applicable

---

## 9. Program-level acceptance criteria

The reorganization is complete only when all of the following are true:

1. `workflows/pipelines/` is the real runtime package and matches the documented structure.
2. Shared infrastructure lives under `pipelines/shared/`; workflow-owned code lives under `pipelines/workflows/<workflow>/`.
3. State models are split into one shared state module and one state module per workflow with no duplication.
4. Both workflows still execute successfully after the move.
5. Structured logging is standardized across node and non-node runtime code.
6. Template-upload node/module names no longer rely on the redundant `upload_` prefix in the real package.
7. Tests run from `workflows/` and pass with `pytest -q`.
8. Temporary `comicbook` compatibility wrappers are removed by the end of TG5.
9. Documentation triad, indexes, and ADR-0002 reflect the implemented final state.
10. No non-historical runtime dependency on `ComicBook/comicbook/` remains.

---

## 10. Out-of-scope work

This guide does **not** authorize or require:

- new workflow features unrelated to the move
- database-schema redesign unrelated to module placement
- new non-stdlib logging dependencies
- a forced rename of all `COMICBOOK_*` env vars
- performance tuning unrelated to the migration
- redesigning workflow behavior while files are being moved

Keep the migration focused. Any new requirement discovered during implementation should either fit clearly inside the active TaskGroup or be captured as a follow-up planning update.
