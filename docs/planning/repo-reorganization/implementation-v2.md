# Technical Implementation Guide: Repository Reorganization (v2)

| Field | Value |
| --- | --- |
| Status | Draft for implementation (replacement for `implementation.md`) |
| Version | 2.0 |
| Date | 2026-04-25 |
| Source plan | `docs/planning/repo-reorganization/plan.md` |
| Sibling handoff | `docs/planning/repo-reorganization/implementation-handoff.md` |
| ADR | `docs/planning/adr/ADR-0002-repo-reorganization.md` |
| Audience | Implementation team executing the migration end-to-end |
| Authority | This document is the single source of truth for execution. The plan provides the *why*; this guide provides the *how*. Implementation must not require reopening the plan or other planning docs to make day-to-day decisions. |
| Execution mode | Sequential TaskGroups (TG1 → TG5). Within a TaskGroup, tasks are also numbered and ordered by dependency. |

> **Hard stop.** This guide does not authorize implementation. Implementation may begin only after the user invokes `/implement-next <implementation-doc> [handoff-doc]`. See § 14.

---

## How to use this document

Read sections 1 through 6 once before starting. Sections 7 through 11 are the execution body — open the active TaskGroup section in section 8 and follow it task by task. Sections 12 through 15 are reference material the implementer may need at any point. Appendices A through F provide explicit copy-paste material (templates, tables, commands).

When repository reality conflicts with this guide, **stop and reconcile** before continuing. Update this guide first, then execute. Do not silently absorb adjacent work into a TaskGroup.

---

## 1. Executive summary

The repository today ships two LangGraph workflows (image prompt generation and template upload) inside a single flat `ComicBook/comicbook/` package, with shared infrastructure mixed in alongside workflow-specific code. The reorganization moves the codebase into a per-workflow layout under `workflows/pipelines/`, splits state ownership, standardizes logging through one shared module, and updates documentation and agent instructions to match.

The migration is staged across five TaskGroups so each step ends in a runnable, testable repository. A temporary `workflows/comicbook/` compatibility package keeps legacy import paths alive during the transition and is deleted in TG5. The migration does **not** change SQLite schemas, runtime env-var names other than logging controls, persistence semantics, or workflow behavior.

The migration is complete when (a) `workflows/pipelines/` is the real runtime package, (b) state is split into shared plus per-workflow modules with no duplication, (c) every node and non-node module emits structured logs through the shared logging module, (d) the `comicbook` compatibility package is deleted, (e) ADR-0002 is marked **Accepted and Implemented**, and (f) the documentation triad and indexes describe the realized state.

---

## 2. Verified repository baseline

The following baseline was verified at the time this guide was written. Implementers must re-verify against `git status` before starting any TaskGroup; if reality differs, update this section first.

### 2.1 Legacy runtime tree (still authoritative for behavior)

`ComicBook/comicbook/` is the runtime package today. It contains the following Python modules, all currently imported as `comicbook.*`:

`__init__.py`, `config.py`, `db.py`, `deps.py`, `execution.py`, `fingerprint.py`, `graph.py`, `image_client.py`, `input_file.py`, `metadata_prompts.py`, `repo_protection.py`, `router_llm.py`, `router_prompts.py`, `run.py`, `runtime_deps.py`, `state.py`, `upload_graph.py`, `upload_run.py`, `pricing.json`, and `nodes/` containing `cache_lookup.py`, `generate_images_serial.py`, `ingest.py`, `load_templates.py`, `persist_template.py`, `router.py`, `summarize.py`, `upload_backfill_metadata.py`, `upload_decide_write_mode.py`, `upload_load_file.py`, `upload_parse_and_validate.py`, `upload_persist.py`, `upload_resume_filter.py`, `upload_summarize.py`.

Adjacent legacy assets: `ComicBook/tests/` (pytest tree), `ComicBook/examples/`, `ComicBook/DoNotChange/` (protected content), `ComicBook/.env.example`, `ComicBook/pyproject.toml`.

### 2.2 Target tree (partially seeded, partially populated)

`workflows/` already exists and contains the following:

- `workflows/README.md` — setup notes maintained during the migration.
- `workflows/pyproject.toml` — target-tree project metadata (added during TG2 bootstrap; keeps compatibility with `comicbook*` package discovery during the shim window).
- `workflows/.env.example` — moved from `ComicBook/.env.example`.
- `workflows/pipelines/__init__.py`, `workflows/pipelines/workflows/__init__.py`.
- `workflows/pipelines/shared/__init__.py` plus moved-source-of-truth modules: `logging.py`, `config.py`, `deps.py`, `runtime_deps.py`, `execution.py`, `db.py`, `fingerprint.py`, `repo_protection.py`. (`state.py` is **not** yet split — see TG3.)
- `workflows/pipelines/workflows/image_prompt_gen/` containing `__init__.py`, `graph.py`, `run.py`, `input_file.py`, `pricing.json`, `prompts/router_prompts.py`, `prompts/metadata_prompts.py`, `adapters/router_llm.py`, `adapters/image_client.py`. **No `state.py` yet** and **no `nodes/`** under this folder yet (legacy nodes still live under `ComicBook/comicbook/nodes/`).
- `workflows/pipelines/workflows/template_upload/` containing `__init__.py`, `graph.py`, `run.py`. **No `state.py` yet** and **no `nodes/`** under this folder yet.
- `workflows/comicbook/` — temporary compatibility package. It contains explicit wrapper modules for each shared module that has moved (`config.py`, `db.py`, `deps.py`, `execution.py`, `fingerprint.py`, `repo_protection.py`, `runtime_deps.py`), wrapper modules for moved entry points and graphs (`run.py`, `upload_run.py`, `graph.py`, `upload_graph.py`), wrapper modules for moved image helpers (`image_client.py`, `input_file.py`, `metadata_prompts.py`, `router_llm.py`, `router_prompts.py`), a wrapper `state.py` that re-exports the still-legacy combined state model, and a `nodes/` subpackage with wrappers for every legacy node module. `workflows/comicbook/__init__.py` exposes the package-root `upload_templates` convenience export.
- `workflows/tests/` — partially populated. Currently contains `tests/shared/test_logging.py`, `tests/shared/test_config_and_compat_state.py`, `tests/shared/test_compat_state_and_nodes.py`, `tests/shared/test_runtime_deps.py`, `tests/shared/test_fingerprint.py`, plus `tests/image_prompt_gen/` (graph scenarios, helper tests, budget guard, example single-portrait, node ingest/summarize) and `tests/template_upload/` (graph scenarios, run CLI, preflight nodes, backfill, persist). Many legacy `ComicBook/tests/` files still exist alongside their relocated counterparts.

### 2.3 Documentation tree

Planning, business, and developer triads exist for `repo-reorganization`, `image-prompt-gen-workflow` (the image-workflow folder used a mixed-case legacy slug when this guide was authored and is normalized during TG2), `template-upload-workflow`, and `implementation-execution-agent`. `docs/standards/repo-structure.md`, `docs/standards/logging-standards.md`, `docs/standards/index.md`, `AGENTS.md`, `opencode.json`, and every `.opencode/agents/*.md` already describe the target layout and logging gate.

### 2.4 Behaviors that must be preserved

Unless a TaskGroup explicitly changes them, the following must remain stable end-to-end:

- both workflows execute and pass tests at the end of every TaskGroup;
- SQLite schema, DAO behavior, run-lock semantics, and persisted field names are unchanged;
- `DoNotChange/` content remains protected and outside the Python package;
- no third-party logging dependency is introduced;
- pytest remains the only test runner;
- file moves preserve git history (`git mv`);
- existing `COMICBOOK_*` env vars keep their names and meanings (only logging vars use the new `PIPELINES_LOG_*` namespace);
- workflow CLI invocations continue to work for operators, even if the import path under the hood changes.

---

## 3. Locked decisions and resolved ambiguities

Each item below resolves a place where the plan was underspecified or where it implied a step that does not match repository reality.

**3.1 — The "ComicBook → workflows" rename is a *convergence*, not a filesystem rename.** `workflows/` already exists with a partial target package and a temporary `comicbook` shim. The implementation moves source-controlled assets out of `ComicBook/` into `workflows/`, retires legacy paths only after their replacements are green, and never attempts a single-shot directory rename.

**3.2 — Phase 1 of the plan is split between TG1 (logging foundation in target tree) and TG2 (runtime adoption).** Wiring legacy `ComicBook/comicbook/runtime_deps.py` to `pipelines.shared.logging` would require a `sys.path` hack, which violates the single-source-of-truth rule. TG1 finalizes and tests the shared logging module in `workflows/pipelines/shared/logging.py`. TG2 adopts it from `runtime_deps.py` and CLI entry points after they have been moved into `pipelines.*`.

**3.3 — Compatibility is a full temporary package, not a single `__init__.py` shim.** The existing tests and likely external scripts import many legacy submodules (`comicbook.graph`, `comicbook.run`, `comicbook.upload_run`, `comicbook.db`, `comicbook.nodes.upload_load_file`, etc.). The compatibility surface lives under `workflows/comicbook/` as explicit wrapper modules. Do not rely on `sys.path` tricks, dynamic `sys.modules` patching, or `__init__.py` re-export glue as the primary mechanism.

**3.4 — Distribution metadata stays conservative during the shim window.** The `pipelines` import package is the real package after TG2. Package discovery additionally includes `comicbook*` while the shim exists. The distribution name is **not** renamed.

**3.5 — `COMICBOOK_*` env vars are out of scope.** Only logging controls use the new namespace: `PIPELINES_LOG_FORMAT` (default `json`, opt-in `text`) and `PIPELINES_LOG_LEVEL` (default `INFO`).

**3.6 — TG1 uses a narrow target-tree pytest invocation with `PYTHONPATH=workflows`.** TG2 onward uses `pytest -q` from `workflows/` driven by `workflows/pyproject.toml`.

**3.7 — ADR-0002 status progression.** The ADR is set to **Accepted** when TG1 lands and to **Accepted and Implemented** at the end of TG5. Use the ADR's wording, not the plan's looser wording.

**3.8 — No persistence-schema or behavior redesign.** Any persistence touch during these TaskGroups must be strictly mechanical (import path updates) or logging-supporting (new structured fields).

**3.9 — Doc-slug normalization runs in TG2.** Normalizing the mixed-case image-workflow doc slug to `image-prompt-gen-workflow` across `docs/planning/`, `docs/business/`, `docs/developer/`, and every index that links to those folders happens in TG2 because it pairs naturally with the directory move.

**3.10 — Examples folder placement.** During the migration, `ComicBook/examples/` moves to `workflows/examples/` (repo-level under the new root). Per-workflow `examples/` folders are deferred until a third workflow is added.

**3.11 — Wrapper modules contain no logic.** Compatibility wrappers re-export only. Any behavior that appears in a wrapper signals that the wrapper is the wrong abstraction; move that behavior into the real `pipelines.*` module instead.

**3.12 — Slice discipline.** TaskGroups are sequential. Within a TaskGroup, tasks are also ordered by dependency. Do not reorder tasks unless this guide is updated first. Do not start a later TaskGroup until the earlier one's exit criteria are met and verified.

---

## 4. Target architecture (post-TG5)

### 4.1 Final repository layout

```
.
├── AGENTS.md
├── opencode.json
├── .opencode/
├── docs/
└── workflows/
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
    │       │   │   ├── __init__.py
    │       │   │   ├── image_client.py
    │       │   │   └── router_llm.py
    │       │   ├── prompts/
    │       │   │   ├── __init__.py
    │       │   │   ├── metadata_prompts.py
    │       │   │   └── router_prompts.py
    │       │   └── nodes/
    │       │       ├── __init__.py
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
    │               ├── __init__.py
    │               ├── backfill_metadata.py
    │               ├── decide_write_mode.py
    │               ├── load_file.py
    │               ├── parse_and_validate.py
    │               ├── persist.py
    │               ├── resume_filter.py
    │               └── summarize.py
    └── tests/
        ├── shared/
        ├── image_prompt_gen/
        ├── template_upload/
        └── integration/
```

`ComicBook/` and `workflows/comicbook/` are deleted in TG5.

### 4.2 Module ownership rules

`pipelines.shared` owns cross-workflow concerns only: configuration loading, the dependency container, runtime construction, SQLite access, repo protection, fingerprinting, execution orchestration, and structured logging. `pipelines.workflows.<workflow>` owns its graph, entry point, workflow-only state, prompts, adapters, and nodes. A workflow-local module that gains a second importer from another workflow is promoted to `pipelines.shared/` (as part of TG5 if it is detected during this migration; otherwise as a follow-up).

### 4.3 Runtime contracts

Image-workflow CLI: `python -m pipelines.workflows.image_prompt_gen.run …`. Template-upload CLI: `python -m pipelines.workflows.template_upload.run …`. Shared helpers are imported only from `pipelines.shared.*`. Nodes keep their existing callable shape — `def node(state, deps) -> state_delta`. Wrapper modules in `workflows/comicbook/` re-export the new homes and contain no logic.

### 4.4 State split contract (locked)

`pipelines/shared/state.py` contains only cross-workflow types: `WorkflowModel`, `WorkflowError`, `UsageTotals`, `RunSummary`, `RunStatus`, and any status helpers used by reporting in both workflows.

`pipelines/workflows/image_prompt_gen/state.py` contains image-workflow-only types: `RunState`, `TemplateSummary`, `NewTemplateDraft`, `PromptPlanItem`, `RouterTemplateDecision`, `RouterPlan`, `RenderedPrompt`, `ImageResult`, and image-workflow-only literals `ImageSize`, `ImageQuality`, `RouterModel`, `ImageResultStatus`.

`pipelines/workflows/template_upload/state.py` contains template-upload-only types: `ImportRunState`, `TemplateImportRow`, `TemplateImportRowResult`, `ImportRowStatus`, `ImportWriteMode`.

No type may exist in more than one file. Each workflow `state.py` imports its bases from `pipelines.shared.state`. Shared modules must never import from a workflow `state.py`.

### 4.5 Persistence contract

`pipelines.shared.db` is the only home of SQLite access. Run-lock behavior, persisted field names, and report contents do not change. No new tables, columns, or migrations are introduced because of the reorganization.

### 4.6 Observability contract

Required fields on every record: `timestamp`, `level`, `logger`, `event`, `workflow`, `run_id`, `message`. Records originating inside a graph node also include `node`. Default format is JSON; `PIPELINES_LOG_FORMAT=text` switches to console-readable mode for local development. Default level is `INFO`; `PIPELINES_LOG_LEVEL=DEBUG` widens the floor.

Nodes emit through `log_node_event(deps, state, event, **fields)`. Non-node code uses `get_logger(__name__)` plus `log_event(logger, event, *, workflow=…, run_id=…, **fields)`. Direct `deps.logger.*` calls inside nodes are forbidden after TG4. See appendix C for the field reference and example records.

### 4.7 Failure-handling contract

Every TaskGroup ends in a green pytest run. Each TaskGroup explicitly enumerates the temporary compatibility code it introduces, and every later TaskGroup explicitly enumerates the items it deletes. Use the smallest test scope first, then broaden. Do not delete a legacy import path until its replacement and any compatibility wrapper covering it are proven by tests.

### 4.8 Execution discipline

This guide is a contract. Only work explicitly listed in the active TaskGroup's *In scope* section and *Detailed task list* is authorized. If repository reality conflicts with the guide in a way that would change scope, sequencing, ownership, contracts, tests, observability, acceptance criteria, or rollout behavior, **stop and update this guide before continuing**. Do not silently expand a TaskGroup. If a later slice discovers missing technical detail, update this guide first.

---

## 5. Cross-cutting requirements

### 5.1 Testing requirements

Use pytest for every behavioral change. Prefer the narrowest failing scope first, broaden after focused green results, and finish each TaskGroup with a full `pytest -q` from `workflows/` (TG1 uses `PYTHONPATH=workflows pytest -q workflows/tests/shared/test_logging.py` because the package is not yet installed). Compatibility wrappers are testable surfaces — test that wrapper imports return the same module object as the real one (`is` identity) and that key public names are re-exported. Every TaskGroup adds at least one new or updated test if it changes behavior; cosmetic-only TaskGroups document why no test is needed.

Test layout in the target tree mirrors the package: `workflows/tests/shared/`, `workflows/tests/image_prompt_gen/`, `workflows/tests/template_upload/`, `workflows/tests/integration/`. Cross-workflow integration tests use the `integration/` subtree; everything else lives in the workflow folder it exercises.

### 5.2 Documentation requirements

Every TaskGroup carries the documentation gate. The triad (`docs/planning/<slug>/`, `docs/business/<slug>/`, `docs/developer/<slug>/`) plus the impacted `index.md` files at every level must reflect what the TaskGroup actually landed. If a TaskGroup changes the developer-facing layout (new package paths, new test layout, new env vars), the developer doc updates in the same TaskGroup. If it changes operator-facing behavior (CLI invocation, log format), the business doc updates too. ADR-0002 status updates in TG1 (Accepted) and TG5 (Accepted and Implemented).

### 5.3 Observability requirements

Production logs remain machine-parseable JSON by default. Any new logging call site honors existing redaction flags (`redact_prompts`, `redact_style_text_in_logs`). No phase is complete until operators can identify `workflow`, `run_id`, and node context from log lines where applicable.

### 5.4 Code-quality requirements

Imports use absolute `pipelines.*` paths in moved code; relative imports are reserved for intra-package convenience inside the same subpackage. Public symbols use explicit `__all__` where the surface is part of the migration contract (state modules, the logging module, both `__init__.py` files inside `pipelines/`). Type hints stay on every public function moved. No mass-formatting changes in the same commit as a move; formatting passes happen separately if needed.

### 5.5 Rollback policy

If a TaskGroup fails partway through, revert the in-progress commit cluster and leave the previous TaskGroup's exit-criteria state. Do not partial-merge a TaskGroup. The compatibility wrappers ensure that any TG2-onwards revert returns the repo to a runnable state because legacy imports keep working through the shim window.

---

## 6. TaskGroup overview

The migration runs as five sequential TaskGroups. TG1 is the only one that can start without prior migration work. Each later TaskGroup depends on the prior one's exit criteria.

| ID | Title | Depends on | Primary outcome |
| --- | --- | --- | --- |
| TG1 | Shared logging foundation | none | `pipelines.shared.logging` matches the standard, fully tested in the target tree. |
| TG2 | Move package + tests into `workflows/`, add `comicbook` shim, normalize doc slugs, adopt non-node logging | TG1 | `pipelines` is the real runtime package; legacy imports still work through the shim. |
| TG3 | Split state modules | TG2 | Three state modules with no duplication; every importer points at the right home. |
| TG4 | Adopt node logging + remove `upload_` prefix from template-upload nodes | TG3 | Every runtime emit goes through the shared helpers; template-upload module/function names no longer carry redundant prefixes. |
| TG5 | Remove the `comicbook` shim, sweep stale references, close docs and ADR | TG4 | No legacy path remains; ADR-0002 is **Accepted and Implemented**. |

Each TaskGroup ends with a runnable, testable repository.

---

## 7. Reading the TaskGroup sections

Each TaskGroup section in section 8 has the same structure. Read it in order:

1. **Goal** — the single outcome the TaskGroup must produce.
2. **Dependencies** — verifiable preconditions; check them before starting.
3. **Pre-flight checklist** — concrete commands or grep patterns to confirm the prereqs.
4. **In scope** — exhaustive list of work this TaskGroup owns.
5. **Out of scope** — explicit list of nearby work that is *not* allowed in this TaskGroup.
6. **Detailed task list** — numbered tasks (e.g. `TG2.T1`, `TG2.T2`) with files, commands, and snippets. Tasks are ordered by dependency. Each task ends with a focused verification step.
7. **Expected files (full enumeration)** — every file the TaskGroup creates, modifies, or deletes.
8. **Test plan** — required test additions or updates and the verification sequence.
9. **Documentation impact** — explicit list of docs to update.
10. **Exit criteria (verifiable)** — the green-bar conditions; each is a command or grep that can be run.
11. **Rollback notes** — what to do if the TaskGroup must be reverted partway.
12. **Handoff to the next TaskGroup** — facts the next TaskGroup needs.

---

## 8. TaskGroup details

### TG1 — Shared logging foundation

**Goal.** Make `workflows/pipelines/shared/logging.py` match `docs/standards/logging-standards.md` exactly, and back it with focused tests under `workflows/tests/shared/test_logging.py`.

**Dependencies.** None.

**Pre-flight checklist.**

- `workflows/pipelines/shared/logging.py` exists. (`ls workflows/pipelines/shared/logging.py`)
- `docs/standards/logging-standards.md` exists and reflects the latest contract. (`grep -n 'log_node_event' docs/standards/logging-standards.md`)
- No legacy module imports `pipelines.shared.logging` yet. (`grep -RIn 'pipelines.shared.logging' ComicBook/`)

**In scope.**

- finalize the public surface and behavior of `workflows/pipelines/shared/logging.py` (`get_logger`, `JsonFormatter`, `NodeLogContext`, `log_event`, `log_node_event`);
- add focused unit tests under `workflows/tests/shared/test_logging.py`;
- align module behavior with the existing logging standard.

**Out of scope.**

- rewiring legacy `ComicBook/comicbook/` modules to import the target logger (that happens in TG2);
- any package move, wrapper creation, or test relocation outside logging coverage;
- workflow renames, state splits, or runtime CLI changes.

**Detailed task list.**

**TG1.T1 — Audit `pipelines/shared/logging.py` against the standard.** Open `workflows/pipelines/shared/logging.py` and `docs/standards/logging-standards.md` side by side. Confirm that the module exports exactly: `get_logger(name) -> logging.Logger`, `JsonFormatter` (a `logging.Formatter` subclass), `NodeLogContext` (dataclass with `workflow`, `run_id`, optional `node`), `log_event(logger, event, *, workflow="shared", run_id=None, **fields) -> None`, and `log_node_event(deps, state, event, *, level="INFO", message=None, **fields) -> None`. Document any deltas. Verification: produce a written delta list (in this task's commit message or scratch notes) before T2.

**TG1.T2 — Bring the module up to spec.** Apply the deltas identified in T1. Required behaviors:

- `JsonFormatter` produces a JSON object on a single line, ordered for stable diffing. Required keys: `timestamp` (ISO-8601 UTC with milliseconds, e.g. `2026-04-25T18:32:11.482Z`), `level`, `logger`, `event`, `workflow`, `run_id`, `message`. Optional keys when present on the record's `extra`: `node`, `component`, `duration_ms`, `error.code`, `error.message`, `error.retryable`, plus any `extra` payload nested under an `extra` object.
- `get_logger(name)` returns a logger configured with one stdout `StreamHandler` carrying `JsonFormatter` (text mode if `PIPELINES_LOG_FORMAT=text`). Idempotent: calling it twice for the same name does not duplicate handlers.
- `log_event(logger, event, *, workflow="shared", run_id=None, **fields)` emits one record at `INFO` (override via a `level` kwarg) with the standard fields populated through `extra`.
- `log_node_event(deps, state, event, *, level="INFO", message=None, **fields)` resolves `workflow` and `run_id` from `state` (or `state.workflow` / `state.run_id` attribute access fallbacks), resolves `node` from an explicit kwarg or the calling frame (`sys._getframe(1).f_code.co_name`), and emits through `deps.logger`.
- Sensitive payloads honor existing flags (`deps.config.redact_prompts`, `deps.config.redact_style_text_in_logs`).

A reference skeleton is in **Appendix B** below; copy and adapt as needed but the public surface is non-negotiable.

**TG1.T3 — Add focused tests.** Create `workflows/tests/shared/test_logging.py` covering at minimum these cases (fixture: capture log records via `caplog` or a custom in-memory handler):

- `JsonFormatter` produces every required field with the correct types;
- promoted optional fields (`node`, `component`, `duration_ms`, `error.code`) appear at top level when set;
- non-promoted extras nest under `extra`;
- exception serialization includes `error.code`, `error.message`, and a stack-trace-friendly summary;
- `get_logger(name)` returns the same logger and does not stack handlers when called repeatedly;
- `log_event(...)` populates `workflow`, `run_id`, `event`, `message`;
- `log_node_event(deps, state, event, ...)` populates `workflow`, `run_id`, `event`, `node`;
- `PIPELINES_LOG_FORMAT=text` switches to a human-readable format without dropping required keys.

Test fixtures may construct fake `Deps` and `state` objects locally; do not reach into legacy `ComicBook/comicbook/`.

**TG1.T4 — Run the focused scope.** From the repository root:

```bash
PYTHONPATH=workflows pytest -q workflows/tests/shared/test_logging.py
```

All cases must pass. If a case fails because the standard is wrong, **update the standard in the same TaskGroup** and re-run.

**TG1.T5 — Update planning, business, developer docs and the ADR.** Record that TG1 has landed, set ADR-0002 status to **Accepted** (per § 3.7), and update the impacted indexes. Do not claim runtime adoption — that belongs to TG2.

**Expected files (full enumeration).**

- modified: `workflows/pipelines/shared/logging.py`
- created: `workflows/tests/shared/test_logging.py`
- modified: `docs/planning/repo-reorganization/index.md`
- modified: `docs/business/repo-reorganization/index.md`
- modified: `docs/developer/repo-reorganization/index.md`
- modified: `docs/planning/adr/ADR-0002-repo-reorganization.md`
- modified: `docs/planning/repo-reorganization/implementation-handoff.md`

**Test plan.** Verification command: `PYTHONPATH=workflows pytest -q workflows/tests/shared/test_logging.py`. Required assertions cover the bullets in TG1.T3.

**Documentation impact.** Triad updates noting that the logging foundation has landed; ADR-0002 → **Accepted**; index updates listing the new test file under planning if relevant. No business-facing or operator-facing change yet.

**Exit criteria.**

- `PYTHONPATH=workflows pytest -q workflows/tests/shared/test_logging.py` passes.
- `grep -RIn 'pipelines.shared.logging' ComicBook/` returns nothing.
- ADR-0002 status line reads **Accepted**.
- Triad indexes mention TG1 completion.

**Rollback notes.** If TG1 must be reverted, drop the new test file and revert the `logging.py` change. The repository remains in its pre-TG1 state. Legacy `ComicBook/` is untouched.

**Handoff to TG2.** TG2 may treat `pipelines.shared.logging` as production-ready. If TG1 surfaces a standard mismatch, the standard must be updated before TG2 starts.

---

### TG2 — Move package + tests into `workflows/`, add the `comicbook` shim, normalize doc slugs, adopt non-node logging

**Goal.** Make `workflows/` the real runtime root. Move every shared module, both workflow graphs, both run modules, image-helper modules, the pricing asset, examples, and `DoNotChange/` into the target ownership layout. Move tests into `workflows/tests/`. Create the `workflows/comicbook/` compatibility package as the only legacy import surface. Adopt the shared logger in non-node runtime code. Normalize the image-workflow doc slug to `image-prompt-gen-workflow`.

TG2 does **not** split state, does **not** rename `upload_*` template-upload modules, and does **not** remove any compatibility wrapper.

**Dependencies.** TG1 complete (exit criteria green).

**Pre-flight checklist.**

- TG1 exit criteria all green (`pytest -q workflows/tests/shared/test_logging.py`).
- `git status` clean before starting; `git log -1` shows the last TG1 commit.
- `workflows/pyproject.toml` exists (TG2 bootstrap may already be partially complete — see § 2.2).

**In scope.**

- bootstrap `workflows/pyproject.toml` with project metadata that drives target-tree pytest from `workflows/` and includes both `pipelines*` and (temporary) `comicbook*` in package discovery;
- `git mv` moves of every file in **Appendix A** that has not already been moved;
- import rewiring inside moved files so they import from `pipelines.*`;
- non-node logging adoption: `pipelines.shared.runtime_deps` uses `get_logger(__name__)`; both run modules emit lifecycle events through `log_event(...)`;
- creation of explicit wrapper modules under `workflows/comicbook/` for every legacy import path (see **Appendix D**);
- `workflows/comicbook/nodes/` wrapper subpackage with one wrapper per legacy node module;
- conversion of every `ComicBook/comicbook/*.py` module into a thin compatibility wrapper that re-exports the moved module (interim state through the rest of TG2; deleted in TG5);
- update of `.env.example` location, repo-protection path constants, pre-commit config references, and any pytest working-directory documentation to point at `workflows/`;
- relocation of every test from `ComicBook/tests/` into `workflows/tests/` under the appropriate subfolder;
- rename of the mixed-case image-workflow doc folders under `docs/planning/`, `docs/business/`, and `docs/developer/` to `image-prompt-gen-workflow` (and update of every link to those folders).

**Out of scope.**

- splitting `state.py` (TG3);
- removing the `upload_` prefix from template-upload node modules or function names (TG4);
- removing any compatibility wrapper or legacy path (TG5);
- any change to SQLite schema, env-var names other than logging controls, or workflow behavior;
- introducing third-party logging dependencies.

**Detailed task list.**

TG2 is large and benefits from sub-slices. Implementers may execute the tasks below as one slice or split them along the natural boundaries (shared modules, workflow modules, helpers, tests, docs). Whatever cadence is chosen, each commit must end in a green test scope.

**TG2.T1 — Verify and finalize `workflows/pyproject.toml`.** Use **Appendix E** as the canonical template. Required configuration:

- `[project] name = "pipelines"` (do not rename the distribution; keep it stable across the migration);
- `[tool.setuptools.packages.find] include = ["pipelines*", "comicbook*"]`;
- `[tool.pytest.ini_options] testpaths = ["tests"]`, `pythonpath = ["."]`;
- copy any project-level dependencies from `ComicBook/pyproject.toml` verbatim;
- migrate any existing tool config (ruff, mypy, etc.) verbatim.

Verification: `cd workflows && pytest -q tests/shared/test_logging.py` (expect existing TG1 test to pass under the `workflows/` working directory once `pyproject.toml` is in place).

**TG2.T2 — Move `.env.example`.** `git mv ComicBook/.env.example workflows/.env.example`. Verify that no source-controlled file references the old path.

**TG2.T3 — Move shared modules with `git mv`.** Move each of the following shared modules using `git mv`. Use **Appendix A** for the full mapping. Move order (dependency-aware): `config.py` → `deps.py` → `repo_protection.py` → `fingerprint.py` → `db.py` → `execution.py` → `runtime_deps.py`. Do not change module contents in this task. Update absolute imports inside each moved module so it imports from `pipelines.shared.*` (and never from `comicbook.*`). After each `git mv`, replace `ComicBook/comicbook/<module>.py` with a thin compatibility wrapper using **Appendix D**'s template.

Verification per module: `python -c "import pipelines.shared.<module>"` (run from `workflows/` after `pip install -e .`) and `python -c "import comicbook.<module>; assert comicbook.<module>.__name__ == 'pipelines.shared.<module>'"`.

**TG2.T4 — Move workflow entry points and graphs.** Move:

- `ComicBook/comicbook/run.py` → `workflows/pipelines/workflows/image_prompt_gen/run.py`
- `ComicBook/comicbook/graph.py` → `workflows/pipelines/workflows/image_prompt_gen/graph.py`
- `ComicBook/comicbook/upload_run.py` → `workflows/pipelines/workflows/template_upload/run.py`
- `ComicBook/comicbook/upload_graph.py` → `workflows/pipelines/workflows/template_upload/graph.py`

Update imports. Replace each legacy file with a wrapper. Verify: `python -m pipelines.workflows.image_prompt_gen.run --help` and `python -m pipelines.workflows.template_upload.run --help` both work; `python -c "import comicbook.run as r; print(r.__name__)"` returns `pipelines.workflows.image_prompt_gen.run`.

**TG2.T5 — Move image-workflow helpers.** Move:

- `input_file.py` → `workflows/pipelines/workflows/image_prompt_gen/input_file.py`
- `router_prompts.py` → `workflows/pipelines/workflows/image_prompt_gen/prompts/router_prompts.py`
- `metadata_prompts.py` → `workflows/pipelines/workflows/image_prompt_gen/prompts/metadata_prompts.py`
- `router_llm.py` → `workflows/pipelines/workflows/image_prompt_gen/adapters/router_llm.py`
- `image_client.py` → `workflows/pipelines/workflows/image_prompt_gen/adapters/image_client.py`
- `pricing.json` → `workflows/pipelines/workflows/image_prompt_gen/pricing.json`

Add `__init__.py` to the new `prompts/` and `adapters/` subpackages. Update default pricing-path resolution in `runtime_deps.py` so the target-tree pricing asset is the first path tried; keep a temporary fallback to the legacy path until TG5 cleanup. Replace each legacy `comicbook/` module with a wrapper.

**TG2.T6 — Move nodes (mechanical move only).** Move every node from `ComicBook/comicbook/nodes/` to its target home (`pipelines/workflows/image_prompt_gen/nodes/` or `pipelines/workflows/template_upload/nodes/`). Per **Appendix A** mapping. For template-upload nodes, **keep the `upload_*` filenames and function names for now** — renaming happens in TG4. Update imports inside every node so they reference `pipelines.shared.*` and the appropriate workflow package. Replace each legacy node file with a wrapper module.

**TG2.T7 — Move adjacent assets.** `git mv ComicBook/examples workflows/examples`. `git mv ComicBook/DoNotChange workflows/DoNotChange`. Update `pipelines.shared.repo_protection` constants to reference the new `DoNotChange/` path. Update any pre-commit hook or `.gitignore` entry referencing the old paths.

**TG2.T8 — Adopt structured logging in non-node runtime code.** In `pipelines/shared/runtime_deps.py`, replace `logging.getLogger(...)` calls with `get_logger("pipelines.run")`. In `pipelines/workflows/image_prompt_gen/run.py` and `pipelines/workflows/template_upload/run.py`, replace each `logger.info(...)` / `logger.exception(...)` lifecycle event with a `log_event(logger, event, workflow=…, run_id=…, …)` call that carries the standard fields. Node-level logging is **not** changed in TG2; that is TG4's work.

**TG2.T9 — Move tests.** `git mv ComicBook/tests` → `workflows/tests/` with the layout `workflows/tests/shared/`, `workflows/tests/image_prompt_gen/`, `workflows/tests/template_upload/`. For tests that already exist in both trees (relocated during the existing TG2 progress), keep the target-tree copy and delete the legacy copy; verify each pair has identical assertions before deletion. Update test imports so they reference `pipelines.*` directly. Keep one or two thin smoke tests that import via `comicbook.*` to prove the wrapper layer works end-to-end (these live under `workflows/tests/shared/test_compat_*.py` and are deleted in TG5).

**TG2.T10 — Normalize doc-tree slugs.** Rename the mixed-case image-workflow doc directories under `docs/planning/`, `docs/business/`, and `docs/developer/` to `image-prompt-gen-workflow`. Then run a repository-wide grep for the old mixed-case slug and update every remaining reference (indexes, READMEs, agent files, ADRs).

**TG2.T11 — Update tooling references.** `pyproject.toml` (root, if any), `.opencode/agents/*.md` (if they reference paths), `AGENTS.md`, `opencode.json`, and any pre-commit config — update path strings from `ComicBook/` to `workflows/` where the migration has invalidated them.

**TG2.T12 — Run the full target-tree test suite.** From `workflows/`:

```bash
pytest -q tests/shared
pytest -q tests/image_prompt_gen
pytest -q tests/template_upload
pytest -q
```

Each must pass. If any fails because the wrapper layer is incomplete, fix the wrapper rather than the test. If a test was originally legacy-only and depended on import paths that are no longer reachable, port the test to use `pipelines.*` imports.

**TG2.T13 — Update the documentation gate for TG2.** Triad updates (`docs/planning/`, `docs/business/`, `docs/developer/`) explicitly mention: package root is now `workflows/`, the `comicbook` shim is in place, doc slugs are normalized, and non-node logging is adopted. Update every `index.md` whose links changed because of slug normalization. Refresh `workflows/README.md` so it documents the new local-run commands. Do not yet claim node-level logging adoption.

**Expected files (full enumeration).** See **Appendix A** for the complete file-by-file mapping. Every legacy file listed there is moved and replaced with a wrapper; every target file listed there now exists under `workflows/`.

**Test plan.** Sequence:

1. focused per-subtree: `pytest -q tests/shared`, `pytest -q tests/image_prompt_gen`, `pytest -q tests/template_upload`;
2. focused compatibility-shim test: `pytest -q tests/shared/test_compat_*`;
3. full: `pytest -q`.

Required new test types: at least one `is`-identity test asserting that `comicbook.<x>` is the same module object as `pipelines.shared.<x>` (or the workflow path); at least one `python -m pipelines.workflows.image_prompt_gen.run --help`-style smoke; at least one structured-logging assertion confirming the non-node runtime emits records with the required fields.

**Documentation impact.** Triad updates plus impacted indexes; `workflows/README.md` updated; AGENTS.md and `.opencode/agents/*.md` reviewed for any references to legacy paths and updated. ADR-0002 status remains **Accepted** (no change in TG2).

**Exit criteria.**

- `cd workflows && pytest -q` passes from `workflows/`.
- `python -m pipelines.workflows.image_prompt_gen.run --help` runs.
- `python -m pipelines.workflows.template_upload.run --help` runs.
- `grep -RIn 'ComicBook/comicbook' workflows/ docs/ AGENTS.md` returns no functional references (only historical/migration-context references are allowed).
- grep for the old mixed-case image-workflow slug returns nothing inside `docs/`, `AGENTS.md`, or `.opencode/`.
- Every legacy `ComicBook/comicbook/*.py` module is a wrapper or has been removed.
- The `workflows/comicbook/` shim package exists with one wrapper per legacy import path including the `nodes/` subpackage.
- Non-node runtime code emits structured records (verified by a logging-shape test).

**Rollback notes.** If TG2 must abort midway, revert the in-progress commits. Because TG1 was self-contained, the repository returns to a state where logging is ready but no migration has begun. Do not leave a half-moved tree behind.

**Handoff to TG3.** All imports resolve through `pipelines.*` for moved modules; the `comicbook` shim still keeps any straggler legacy callers working. TG3 may now split `state.py` without import-path concerns.

---

### TG3 — Split state modules

**Goal.** Replace the single mixed `pipelines/shared/state.py` (currently re-exporting the legacy combined state) with three final state modules per § 4.4: `pipelines/shared/state.py` (cross-workflow types only), `pipelines/workflows/image_prompt_gen/state.py`, and `pipelines/workflows/template_upload/state.py`. Update every importer.

**Dependencies.** TG2 complete and green.

**Pre-flight checklist.**

- TG2 exit criteria all green.
- `pipelines/workflows/image_prompt_gen/state.py` and `pipelines/workflows/template_upload/state.py` do not yet exist.
- `pipelines/shared/state.py` may exist as a re-export of the legacy combined state — that is fine and is what TG3 replaces.

**In scope.**

- create the three target state modules with the locked contents from § 4.4;
- update every importer (graphs, runs, nodes, shared helpers, tests, wrappers) to use the right state module;
- update the `workflows/comicbook/state.py` wrapper so it re-exports from the new locations to keep legacy `from comicbook.state import …` callers working through TG5;
- preserve `__all__` exports stable enough that the wrapper can re-export everything previously available.

**Out of scope.**

- persistence-schema or report-format changes;
- node-level logging cleanup beyond imports needed for the split (TG4);
- any wrapper deletion (TG5);
- renaming any state-related symbol; only relocating.

**Detailed task list.**

**TG3.T1 — Create `pipelines/shared/state.py`.** Replace the existing re-export shim with the canonical contents: `WorkflowModel`, `WorkflowError`, `UsageTotals`, `RunSummary`, `RunStatus`, and shared status helpers. Keep `__all__` explicit. Move helpers (not just data classes) only if they are referenced from both workflows; otherwise keep them in the workflow they currently serve.

**TG3.T2 — Create `pipelines/workflows/image_prompt_gen/state.py`.** Place all image-workflow-only types listed in § 4.4. Import shared bases via `from pipelines.shared.state import WorkflowModel, …`. Set `__all__`.

**TG3.T3 — Create `pipelines/workflows/template_upload/state.py`.** Place all template-upload-only types listed in § 4.4. Import shared bases. Set `__all__`.

**TG3.T4 — Rewire importers.** Run a focused sweep:

- `grep -RIn 'from pipelines.shared.state import' workflows/pipelines/`
- `grep -RIn 'from pipelines.workflows.image_prompt_gen.state import' workflows/pipelines/`
- `grep -RIn 'from pipelines.workflows.template_upload.state import' workflows/pipelines/`

Update every importer so it pulls from the right module. Specifically: image-workflow nodes/graph/run import their state from `pipelines.workflows.image_prompt_gen.state`; template-upload nodes/graph/run import theirs from `pipelines.workflows.template_upload.state`; shared modules import from `pipelines.shared.state` only.

**TG3.T5 — Update the `workflows/comicbook/state.py` wrapper.** It must continue to expose every name that the legacy `comicbook.state` previously exposed, sourced from the new homes. This keeps any straggler legacy callers (and the smoke tests in `workflows/tests/shared/test_compat_*.py`) working through the shim window.

**TG3.T6 — Sanity check for state-import boundaries.** Confirm with grep that no shared module imports from a workflow `state.py` and that no workflow imports another workflow's `state.py` directly:

```bash
grep -RIn 'from pipelines.workflows.image_prompt_gen.state' workflows/pipelines/shared/
grep -RIn 'from pipelines.workflows.template_upload.state' workflows/pipelines/shared/
grep -RIn 'pipelines.workflows.image_prompt_gen.state' workflows/pipelines/workflows/template_upload/
grep -RIn 'pipelines.workflows.template_upload.state' workflows/pipelines/workflows/image_prompt_gen/
```

Each grep must return empty.

**TG3.T7 — Run pytest.** From `workflows/`:

```bash
pytest -q tests/shared tests/image_prompt_gen tests/template_upload -k state
pytest -q tests/image_prompt_gen tests/template_upload
pytest -q
```

If a workflow regression appears because two workflows shared a literal that has not been duplicated, prefer to put the literal in `pipelines/shared/state.py` rather than duplicating it.

**TG3.T8 — Documentation update.** Update the developer triad doc to record the final state-module ownership map. Note in the planning triad that compatibility wrappers still expose legacy state imports.

**Expected files (full enumeration).**

- modified: `workflows/pipelines/shared/state.py`
- created: `workflows/pipelines/workflows/image_prompt_gen/state.py`
- created: `workflows/pipelines/workflows/template_upload/state.py`
- modified: `workflows/comicbook/state.py`
- modified (importer rewires): every node, graph, run, and test that imports a state symbol; expect updates to ~30+ files;
- modified: `docs/developer/repo-reorganization/index.md`
- modified: `docs/planning/repo-reorganization/index.md`
- modified: `docs/planning/repo-reorganization/implementation-handoff.md`

**Test plan.** Run the focused state scope first, then per-workflow, then full. Add at least one new test asserting that a workflow `state.py` correctly imports and re-uses shared bases (e.g. `pipelines.workflows.image_prompt_gen.state.RunState` is a `TypedDict` whose fields use `pipelines.shared.state.WorkflowError`). Add a boundary test that asserts shared modules do not import from workflow state (this can be a small grep-style test that uses `tokenize` or `ast`).

**Documentation impact.** Developer triad and impacted indexes updated; planning index notes TG3 completion; handoff updated. No business-facing change.

**Exit criteria.**

- All three target state modules exist with the locked contents.
- No type appears in more than one module.
- The boundary greps in TG3.T6 each return empty.
- `pytest -q` passes from `workflows/`.
- `workflows/comicbook/state.py` still re-exports every legacy name.

**Rollback notes.** If TG3 must abort, revert to the TG2 exit state. The single re-exporting `pipelines.shared.state` returns; nothing else needs cleanup.

**Handoff to TG4.** With state ownership clean, node logging adoption can resolve workflow context unambiguously through `state["workflow"]` / `state["run_id"]` (or the equivalent attribute access), and the `upload_*` rename in TG4 will not need to chase state symbols.

---

### TG4 — Adopt node logging and remove the `upload_` prefix

**Goal.** Make the shared logging contract mandatory across runtime code and remove the redundant `upload_` prefix from template-upload module and function names since the directory `pipelines/workflows/template_upload/nodes/` already establishes scope.

**Dependencies.** TG3 complete and green.

**Pre-flight checklist.**

- TG3 exit criteria all green.
- Every node module exists at its target path; only `upload_*` filenames in `pipelines/workflows/template_upload/nodes/` remain to rename.
- `pipelines.shared.logging.log_node_event` exists and tests pass.

**In scope.**

- replace remaining direct `deps.logger.*` and `logging.getLogger(...)` calls inside every node with `log_node_event(...)`;
- replace any straggler non-node runtime emit with `get_logger(...)` + `log_event(...)`;
- ensure every emitted record carries `workflow`, `run_id`, `event`, plus `node` for node-emitted records;
- add focused logging-shape tests where current tests do not assert field presence;
- rename template-upload modules and functions:
  - `pipelines/workflows/template_upload/nodes/upload_load_file.py` → `load_file.py`
  - `upload_parse_and_validate.py` → `parse_and_validate.py`
  - `upload_resume_filter.py` → `resume_filter.py`
  - `upload_backfill_metadata.py` → `backfill_metadata.py`
  - `upload_decide_write_mode.py` → `decide_write_mode.py`
  - `upload_persist.py` → `persist.py`
  - `upload_summarize.py` → `summarize.py`
  - rename each module's primary callable from `upload_<x>` to `<x>` (e.g. `upload_load_file` → `load_file`);
- update graph assembly and any importer to match;
- update `workflows/comicbook/nodes/upload_*.py` wrappers so they continue to re-export the renamed targets (this keeps legacy import paths working until TG5).

**Out of scope.**

- removing the `comicbook` shim (TG5);
- adding new logging fields beyond the standard;
- broader refactors unrelated to logging or naming cleanup;
- changing function signatures beyond what the rename strictly requires.

**Detailed task list.**

**TG4.T1 — Sweep for node-level direct logging.** From `workflows/`:

```bash
grep -RIn 'deps.logger\.\(info\|debug\|warning\|error\|exception\|critical\)' pipelines/workflows/
grep -RIn 'logging.getLogger' pipelines/workflows/
```

Every match inside a node module must be replaced with `log_node_event(...)`. CLI/run-level emits stay on `log_event(...)` if they were not migrated in TG2.

**TG4.T2 — Convert node emit sites.** For each node, convert lifecycle events. Reference pattern (Appendix C also has the canonical pattern):

```python
from pipelines.shared.logging import log_node_event


def persist(state, deps):
    log_node_event(deps, state, "node_started", rows=len(state["rows"]))
    written = 0
    for row in state["rows"]:
        # ... existing logic ...
        written += 1
    log_node_event(
        deps,
        state,
        "node_completed",
        rows_written=written,
        duration_ms=elapsed_ms,
    )
    return {"rows_written": written}
```

Required emit sites per node: `node_started` at entry, `node_completed` at success exit, `node_failed` (with `error.code`, `error.message`, `error.retryable`) on failure paths, plus any existing `INFO`/`WARNING` events ported from the prior implementation.

**TG4.T3 — Rename template-upload nodes.** Use `git mv` to rename the seven node files listed in the In-scope section. Then rename the primary callable in each module. Update graph imports in `pipelines/workflows/template_upload/graph.py` to reference the new module/function names. Update any test that imported the old names.

**TG4.T4 — Update the `comicbook/nodes/upload_*.py` wrappers.** Each existing wrapper must continue to import from the new home:

```python
"""Compatibility wrapper. Removed in TG5."""

from pipelines.workflows.template_upload.nodes.load_file import *  # noqa: F401,F403
from pipelines.workflows.template_upload.nodes.load_file import load_file as upload_load_file  # noqa: F401
```

The `upload_<x>` re-export keeps any straggler legacy caller working without a behavior change.

**TG4.T5 — Add focused logging tests.** Where existing tests do not assert log shape, add at least one test per workflow that:

- runs a representative sample through a graph;
- captures structured records;
- asserts every record carries `workflow`, `run_id`, `event`, plus `node` for node-emitted records.

For node-level tests that did not assert on logs, do not add log assertions there — keep behavior assertions and log-shape assertions separate.

**TG4.T6 — Run tests in layers.** From `workflows/`:

```bash
pytest -q tests/template_upload tests/image_prompt_gen -k log
pytest -q tests/shared tests/image_prompt_gen tests/template_upload
pytest -q
```

**TG4.T7 — Capture sample run output.** Execute a representative run of each workflow with `PIPELINES_LOG_FORMAT=json PIPELINES_LOG_LEVEL=INFO`. Confirm that every log line is parseable JSON and includes the required fields. Save a redacted sample to `workflows/tests/integration/sample_logs/` if such a fixture is added; otherwise document the verification in the handoff doc.

**TG4.T8 — Documentation gate.** Update planning, business, and developer docs to record that structured logging is now the runtime standard (not just a foundation). Update operator-facing references to template-upload modules in the business and developer triads. Update any ADR or standard if a logging field was added or changed (the standard is the source of truth — change it before changing code).

**Expected files (full enumeration).**

- modified: every node module under `pipelines/workflows/image_prompt_gen/nodes/` and `pipelines/workflows/template_upload/nodes/`;
- renamed (`git mv`): seven template-upload node modules listed in the In-scope section;
- modified: `pipelines/workflows/template_upload/graph.py` (import rewires);
- modified: every `workflows/comicbook/nodes/upload_*.py` wrapper (re-export from new module);
- modified: `workflows/tests/template_upload/` and `workflows/tests/image_prompt_gen/` test files that referenced the old `upload_*` names;
- new or modified: at least one logging-shape test per workflow;
- modified: `docs/planning/repo-reorganization/index.md`, `docs/business/repo-reorganization/index.md`, `docs/developer/repo-reorganization/index.md`, `docs/planning/repo-reorganization/implementation-handoff.md`;
- modified (if needed): `docs/standards/logging-standards.md`.

**Test plan.** Three-layer pytest run (focused logging + per-workflow + full), plus the integration-style sample run in TG4.T7. Required new assertions cover record fields, presence of `node` on node-emitted records, and the renamed names.

**Documentation impact.** Triad updates noting full structured-logging adoption and the template-upload rename. Operator-facing module names refreshed in the business doc.

**Exit criteria.**

- `grep -RIn 'deps.logger\.' pipelines/workflows/` returns no matches inside node bodies.
- `grep -RIn 'logging.getLogger' pipelines/workflows/` returns no matches inside node bodies.
- `grep -RIn 'upload_load_file\|upload_parse_and_validate\|upload_resume_filter\|upload_backfill_metadata\|upload_decide_write_mode\|upload_persist\|upload_summarize' pipelines/workflows/template_upload/` returns nothing (only `comicbook/nodes/upload_*.py` may still reference those names, and only as imports).
- `pytest -q` passes from `workflows/`.
- A representative sample run of each workflow produces records with the standard fields.

**Rollback notes.** If TG4 must abort partway, revert the rename and emit-site changes; TG3's state split remains intact and the repository returns to a runnable state.

**Handoff to TG5.** Every runtime emit goes through the shared helpers; template-upload names match the target convention. TG5 may now delete the compatibility shim with confidence.

---

### TG5 — Remove the compatibility shim and close the migration

**Goal.** Delete `workflows/comicbook/`, sweep stale references across code, tests, docs, and agent instructions, promote any module that has gained a second importer, run the full documentation gate, and mark ADR-0002 **Accepted and Implemented**.

**Dependencies.** TG4 complete and green.

**Pre-flight checklist.**

- TG4 exit criteria all green.
- `grep -RIn 'from comicbook' workflows/pipelines/` returns nothing (any such import is a TG5 finding to fix before deletion).
- `grep -RIn 'import comicbook' workflows/pipelines/` returns nothing.
- The compatibility wrapper modules under `workflows/comicbook/` are the only `comicbook` references in the codebase aside from the smoke tests in `workflows/tests/shared/test_compat_*.py`.

**In scope.**

- delete `workflows/comicbook/` recursively, including `nodes/`;
- delete `ComicBook/` (and any remaining legacy file or wrapper there);
- delete the smoke tests under `workflows/tests/shared/test_compat_*.py`;
- run a final sweep across `docs/`, `AGENTS.md`, `.opencode/`, and tooling configs for any remaining legacy references and remove them (or annotate them clearly as historical context where they appear in ADR-0002 background or change-log sections);
- promote any workflow-local module that now has importers from both workflows into `pipelines/shared/`;
- run the full documentation gate;
- mark ADR-0002 **Accepted and Implemented**.

**Out of scope.**

- new workflow features;
- distribution-name renames;
- post-migration refactors that should be planned separately.

**Detailed task list.**

**TG5.T1 — Final sweep before deletion.** From the repo root:

```bash
grep -RIn 'from comicbook' workflows/
grep -RIn 'import comicbook' workflows/
grep -RIn 'ComicBook/' .
```

Resolve every functional reference (rewire to `pipelines.*`). Annotate or remove any documentation reference. The expected state after this task is that the only remaining references are inside `workflows/comicbook/` itself and the compatibility smoke tests.

**TG5.T2 — Delete the compatibility shim.** `git rm -r workflows/comicbook` and `git rm -r ComicBook` (if any subtree of `ComicBook/` still remains; under the TG2 plan, the legacy modules became wrappers and may have been deleted earlier). Delete `workflows/tests/shared/test_compat_*.py`.

**TG5.T3 — Update package discovery.** Edit `workflows/pyproject.toml` so `[tool.setuptools.packages.find] include = ["pipelines*"]`. Remove the `comicbook*` entry. Re-run `pip install -e .` mentally (the implementation team should perform this step in their environment).

**TG5.T4 — Promote shared modules where needed.** If any module under `pipelines/workflows/<a>/` has a second importer from `pipelines/workflows/<b>/`, move it under `pipelines/shared/` and update both importers. Document the promotion in the developer doc.

**TG5.T5 — Run the full test suite.** From `workflows/`:

```bash
pytest -q
```

Required passes. Also run a representative CLI invocation of each workflow.

**TG5.T6 — Documentation gate.**

- Update `docs/planning/repo-reorganization/index.md` to mark the migration complete.
- Update `docs/business/repo-reorganization/index.md` to describe the realized state.
- Update `docs/developer/repo-reorganization/index.md` so the package paths, test layout, and logging adoption match reality with no remaining "to be migrated" caveats.
- Refresh every workflow-specific triad index (`docs/{planning,business,developer}/image-prompt-gen-workflow/index.md`, same for `template-upload-workflow`).
- Refresh `docs/standards/repo-structure.md` only if the realized state diverges from what is currently documented; otherwise the standard is already consistent and no edit is needed.
- Refresh `AGENTS.md` so no agent instruction still points at compatibility paths.
- Refresh every `.opencode/agents/*.md` so permission postures and priorities point at `pipelines.*`.
- Refresh `workflows/README.md` so it reflects the final command surface.

**TG5.T7 — Update ADR-0002.** Set its status to **Accepted and Implemented** and add a one-line implementation-completion note dated to the TG5 close.

**TG5.T8 — Update the implementation-handoff ledger.** Mark every TaskGroup `completed`. Add a final "Migration complete" entry under the session log.

**Expected files (full enumeration).**

- deleted: `workflows/comicbook/**`;
- deleted: `ComicBook/` (any remaining content);
- deleted: `workflows/tests/shared/test_compat_*.py`;
- modified: `workflows/pyproject.toml` (package discovery narrowed);
- moved (if needed): any workflow-local module promoted to `pipelines/shared/`;
- modified: every doc index touched by the cleanup, plus `AGENTS.md`, every `.opencode/agents/*.md` that references migration paths, `workflows/README.md`;
- modified: `docs/planning/adr/ADR-0002-repo-reorganization.md`;
- modified: `docs/planning/repo-reorganization/implementation-handoff.md`.

**Test plan.** Single full `pytest -q` from `workflows/`, plus CLI smoke tests for both workflows. Additionally re-run the cross-cutting greps from TG2/TG4 exit criteria to confirm no legacy reference remains.

**Documentation impact.** Full triad gate plus impacted indexes; ADR-0002 → **Accepted and Implemented**; agent instructions and AGENTS.md refreshed.

**Exit criteria.**

- `workflows/comicbook/` does not exist.
- `ComicBook/` does not exist (or contains only historical artifacts that the team explicitly chooses to keep, documented clearly as historical context).
- `grep -RIn 'comicbook' .` returns only references in ADR-0002 background, change-log, or historical migration notes.
- `pytest -q` passes from `workflows/`.
- ADR-0002 status reads **Accepted and Implemented**.
- Triad indexes describe the final state with no migration-in-progress caveats.

**Rollback notes.** TG5 deletions are non-trivial to undo. The recommended posture is: complete TG5 only when TG4 has been green for at least one verification run on the implementer's machine and a backup branch has been pushed. If TG5 must roll back, restore the deleted shim from the prior commit and reinstate `comicbook*` package discovery; the rest of the codebase keeps working.

**Handoff.** With TG5 complete, this implementation guide is fully executed. Mark the implementation-handoff ledger accordingly. Any further structural change after TG5 should use a fresh planning update or a follow-up ADR.

---

## 9. Cross-TaskGroup verification matrix

| Check | TG1 | TG2 | TG3 | TG4 | TG5 |
| --- | --- | --- | --- | --- | --- |
| `pytest -q` (target tree) green | scoped to `tests/shared/test_logging.py` | full | full | full | full |
| `pipelines.*` imports resolve | n/a | yes | yes | yes | yes |
| `comicbook.*` imports resolve | n/a | yes (via shim) | yes (via shim) | yes (via shim) | **no** |
| Both CLIs run | yes (no change) | yes (target tree) | yes | yes | yes |
| Log records carry standard fields (non-node) | n/a | yes | yes | yes | yes |
| Log records carry standard fields (node) | n/a | partial (existing pattern) | partial | yes | yes |
| State split clean | n/a | n/a | yes | yes | yes |
| Template-upload names cleaned | n/a | n/a | n/a | yes | yes |
| ADR-0002 status | Accepted | Accepted | Accepted | Accepted | Accepted and Implemented |

---

## 10. Program-level acceptance criteria

The migration is accepted when every item below is true:

- `workflows/pipelines/` is the real runtime package and matches § 4.1.
- Shared infrastructure lives under `pipelines/shared/`; workflow-owned code lives under `pipelines/workflows/<workflow>/`.
- State is split into one shared module and one module per workflow with no duplication (§ 4.4).
- Both workflows execute and pass tests with `pytest -q` from `workflows/`.
- Every node-emitted record carries `workflow`, `run_id`, `event`, `node`, `timestamp`, `level`, `logger`, `message`. Every non-node record carries the same minus `node`.
- Template-upload node modules and primary functions no longer carry the `upload_` prefix.
- `workflows/comicbook/` and `ComicBook/` no longer exist (except for historical references that are clearly labeled as such).
- The documentation triad, impacted indexes, AGENTS.md, every `.opencode/agents/*.md`, and `workflows/README.md` describe the realized state.
- ADR-0002 reads **Accepted and Implemented**.

---

## 11. Out of scope (program-wide)

This guide does not authorize: new workflow features, database-schema redesign, performance tuning, third-party logging dependencies, distribution-name rename, `COMICBOOK_*` env-var rename, or workflow behavior changes. Anything discovered during implementation that does not fit into the active TaskGroup is deferred to a follow-up planning update, not absorbed silently.

---

## 12. Open issues and known limitations

The plan flagged two open questions that remain open at the start of execution. They do **not** block any TaskGroup but should be revisited at the named moment.

- *Where should `examples/` live?* Default in this guide is repo-level `workflows/examples/`. Revisit when a third workflow lands.
- *Should the logging standard add a separate correlation ID for nested calls (e.g. `input-file` batch mode)?* Default is no. Revisit if batch logs become hard to disambiguate.

If a TaskGroup uncovers an additional open issue, record it here and update the handoff ledger before proceeding.

---

## 13. Glossary

- **TaskGroup (TG)** — a sequential migration phase, scoped to land in one or a small number of slices and ending in a green test run.
- **Slice** — one commit-sized chunk of work inside a TaskGroup. The `implementation-slice-guard` skill governs slice selection.
- **Wrapper / shim** — a temporary module under `workflows/comicbook/` that re-exports from the moved location to keep legacy import paths alive. Wrappers contain no logic.
- **Compatibility window** — TG2 through TG4 inclusive. Wrappers exist; legacy callers keep working.
- **Documentation triad** — the three doc roots that must stay synchronized: `docs/planning/<slug>/`, `docs/business/<slug>/`, `docs/developer/<slug>/`.

---

## 14. Permission gate

This document is planning material only. It does not authorize any implementation work, even of TG1.

Implementation may begin only after the user invokes `/implement-next docs/planning/repo-reorganization/implementation-v2.md docs/planning/repo-reorganization/implementation-handoff.md` (or names this file specifically).

Generic continuation phrases (`go ahead`, `continue`, `keep going`, `summarize and continue`) do **not** count as approval.

`USER_APPROVAL_REQUIRED: implementation may start only after explicit /implement-next approval`

---

## Appendix A — File-by-file migration mapping

The mapping below is the canonical move list for TG2.T3 through TG2.T6. Every row is a `git mv` (or, where the legacy file becomes a thin wrapper, a `git mv` + replacement). Paths are relative to repo root.

### Shared modules (TG2.T3)

| Legacy path | Target path | TG2 wrapper to create |
| --- | --- | --- |
| `ComicBook/comicbook/__init__.py` | `workflows/pipelines/__init__.py` | `workflows/comicbook/__init__.py` (re-exports `upload_templates` convenience and exposes wrapper modules) |
| `ComicBook/comicbook/config.py` | `workflows/pipelines/shared/config.py` | `workflows/comicbook/config.py` |
| `ComicBook/comicbook/deps.py` | `workflows/pipelines/shared/deps.py` | `workflows/comicbook/deps.py` |
| `ComicBook/comicbook/runtime_deps.py` | `workflows/pipelines/shared/runtime_deps.py` | `workflows/comicbook/runtime_deps.py` |
| `ComicBook/comicbook/execution.py` | `workflows/pipelines/shared/execution.py` | `workflows/comicbook/execution.py` |
| `ComicBook/comicbook/db.py` | `workflows/pipelines/shared/db.py` | `workflows/comicbook/db.py` |
| `ComicBook/comicbook/fingerprint.py` | `workflows/pipelines/shared/fingerprint.py` | `workflows/comicbook/fingerprint.py` |
| `ComicBook/comicbook/repo_protection.py` | `workflows/pipelines/shared/repo_protection.py` | `workflows/comicbook/repo_protection.py` |

### State (TG2 placeholder, TG3 split)

| Legacy path | TG2 target (interim) | TG3 final target |
| --- | --- | --- |
| `ComicBook/comicbook/state.py` (cross-workflow types) | `workflows/pipelines/shared/state.py` (re-export of legacy) | `workflows/pipelines/shared/state.py` (canonical contents) |
| `ComicBook/comicbook/state.py` (image-workflow types) | n/a | `workflows/pipelines/workflows/image_prompt_gen/state.py` |
| `ComicBook/comicbook/state.py` (template-upload types) | n/a | `workflows/pipelines/workflows/template_upload/state.py` |

### Image-prompt-gen workflow (TG2.T4 / T5 / T6)

| Legacy path | Target path | TG2 wrapper |
| --- | --- | --- |
| `ComicBook/comicbook/graph.py` | `workflows/pipelines/workflows/image_prompt_gen/graph.py` | `workflows/comicbook/graph.py` |
| `ComicBook/comicbook/run.py` | `workflows/pipelines/workflows/image_prompt_gen/run.py` | `workflows/comicbook/run.py` |
| `ComicBook/comicbook/input_file.py` | `workflows/pipelines/workflows/image_prompt_gen/input_file.py` | `workflows/comicbook/input_file.py` |
| `ComicBook/comicbook/router_llm.py` | `workflows/pipelines/workflows/image_prompt_gen/adapters/router_llm.py` | `workflows/comicbook/router_llm.py` |
| `ComicBook/comicbook/image_client.py` | `workflows/pipelines/workflows/image_prompt_gen/adapters/image_client.py` | `workflows/comicbook/image_client.py` |
| `ComicBook/comicbook/router_prompts.py` | `workflows/pipelines/workflows/image_prompt_gen/prompts/router_prompts.py` | `workflows/comicbook/router_prompts.py` |
| `ComicBook/comicbook/metadata_prompts.py` | `workflows/pipelines/workflows/image_prompt_gen/prompts/metadata_prompts.py` | `workflows/comicbook/metadata_prompts.py` |
| `ComicBook/comicbook/pricing.json` | `workflows/pipelines/workflows/image_prompt_gen/pricing.json` | n/a (asset, not a Python module) |
| `ComicBook/comicbook/nodes/cache_lookup.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/cache_lookup.py` | `workflows/comicbook/nodes/cache_lookup.py` |
| `ComicBook/comicbook/nodes/generate_images_serial.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/generate_images_serial.py` | `workflows/comicbook/nodes/generate_images_serial.py` |
| `ComicBook/comicbook/nodes/ingest.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/ingest.py` | `workflows/comicbook/nodes/ingest.py` |
| `ComicBook/comicbook/nodes/load_templates.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/load_templates.py` | `workflows/comicbook/nodes/load_templates.py` |
| `ComicBook/comicbook/nodes/persist_template.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/persist_template.py` | `workflows/comicbook/nodes/persist_template.py` |
| `ComicBook/comicbook/nodes/router.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/router.py` | `workflows/comicbook/nodes/router.py` |
| `ComicBook/comicbook/nodes/summarize.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/summarize.py` | `workflows/comicbook/nodes/summarize.py` |

### Template-upload workflow (TG2.T4 / T6 + TG4 rename)

| Legacy path | TG2 target (keeps `upload_` name) | TG4 final target | TG2 wrapper |
| --- | --- | --- | --- |
| `ComicBook/comicbook/upload_graph.py` | `workflows/pipelines/workflows/template_upload/graph.py` | (no rename) | `workflows/comicbook/upload_graph.py` |
| `ComicBook/comicbook/upload_run.py` | `workflows/pipelines/workflows/template_upload/run.py` | (no rename) | `workflows/comicbook/upload_run.py` |
| `ComicBook/comicbook/nodes/upload_load_file.py` | `workflows/pipelines/workflows/template_upload/nodes/upload_load_file.py` | `…/nodes/load_file.py` | `workflows/comicbook/nodes/upload_load_file.py` |
| `ComicBook/comicbook/nodes/upload_parse_and_validate.py` | `…/nodes/upload_parse_and_validate.py` | `…/nodes/parse_and_validate.py` | `workflows/comicbook/nodes/upload_parse_and_validate.py` |
| `ComicBook/comicbook/nodes/upload_resume_filter.py` | `…/nodes/upload_resume_filter.py` | `…/nodes/resume_filter.py` | `workflows/comicbook/nodes/upload_resume_filter.py` |
| `ComicBook/comicbook/nodes/upload_backfill_metadata.py` | `…/nodes/upload_backfill_metadata.py` | `…/nodes/backfill_metadata.py` | `workflows/comicbook/nodes/upload_backfill_metadata.py` |
| `ComicBook/comicbook/nodes/upload_decide_write_mode.py` | `…/nodes/upload_decide_write_mode.py` | `…/nodes/decide_write_mode.py` | `workflows/comicbook/nodes/upload_decide_write_mode.py` |
| `ComicBook/comicbook/nodes/upload_persist.py` | `…/nodes/upload_persist.py` | `…/nodes/persist.py` | `workflows/comicbook/nodes/upload_persist.py` |
| `ComicBook/comicbook/nodes/upload_summarize.py` | `…/nodes/upload_summarize.py` | `…/nodes/summarize.py` | `workflows/comicbook/nodes/upload_summarize.py` |

### Adjacent assets (TG2.T7)

| Legacy path | Target path |
| --- | --- |
| `ComicBook/examples/` | `workflows/examples/` |
| `ComicBook/DoNotChange/` | `workflows/DoNotChange/` (path stays out of the package; `pipelines.shared.repo_protection` constant updated) |
| `ComicBook/.env.example` | `workflows/.env.example` |
| `ComicBook/tests/` | `workflows/tests/` (split into `shared/`, `image_prompt_gen/`, `template_upload/`, `integration/`) |

---

## Appendix B — Reference skeleton for `pipelines/shared/logging.py`

Use this as a starting structure; align to the exact public surface that the standard prescribes. The current module in the target tree may already match; treat any divergence as a TG1 finding to reconcile.

```python
"""Shared structured-logging helpers for the pipelines package."""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

_PROMOTED_FIELDS = (
    "event",
    "workflow",
    "run_id",
    "node",
    "component",
    "duration_ms",
    "error.code",
    "error.message",
    "error.retryable",
)
_REQUIRED_FIELDS = ("timestamp", "level", "logger", "event", "workflow", "run_id", "message")


@dataclass
class NodeLogContext:
    workflow: str
    run_id: Optional[str] = None
    node: Optional[str] = None


class JsonFormatter(logging.Formatter):
    """Serialize log records as a single-line JSON object with required fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras: Mapping[str, Any] = getattr(record, "_pipelines_extras", {}) or {}
        for key in _PROMOTED_FIELDS:
            if key in extras:
                payload[key] = extras[key]
        for required in _REQUIRED_FIELDS:
            payload.setdefault(required, None)
        nested = {k: v for k, v in extras.items() if k not in _PROMOTED_FIELDS}
        if nested:
            payload["extra"] = nested
        if record.exc_info:
            payload.setdefault("error.code", record.exc_info[0].__name__)
            payload.setdefault("error.message", str(record.exc_info[1]))
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with one stdout handler. Idempotent."""
    logger = logging.getLogger(name)
    if not getattr(logger, "_pipelines_configured", False):
        handler = logging.StreamHandler(stream=sys.stdout)
        if os.environ.get("PIPELINES_LOG_FORMAT", "json").lower() == "text":
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        else:
            handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(os.environ.get("PIPELINES_LOG_LEVEL", "INFO"))
        logger.propagate = False
        logger._pipelines_configured = True  # type: ignore[attr-defined]
    return logger


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    workflow: str = "shared",
    run_id: Optional[str] = None,
    level: str = "INFO",
    message: Optional[str] = None,
    **fields: Any,
) -> None:
    extras = {"event": event, "workflow": workflow, "run_id": run_id, **fields}
    logger.log(getattr(logging, level), message or event, extra={"_pipelines_extras": extras})


def log_node_event(
    deps: Any,
    state: Any,
    event: str,
    *,
    level: str = "INFO",
    message: Optional[str] = None,
    **fields: Any,
) -> None:
    workflow = _resolve(state, "workflow", default="shared")
    run_id = _resolve(state, "run_id", default=None)
    node = fields.pop("node", None) or sys._getframe(1).f_code.co_name
    extras = {
        "event": event,
        "workflow": workflow,
        "run_id": run_id,
        "node": node,
        **fields,
    }
    deps.logger.log(getattr(logging, level), message or event, extra={"_pipelines_extras": extras})


def _resolve(state: Any, key: str, *, default: Any) -> Any:
    if isinstance(state, Mapping):
        return state.get(key, default)
    return getattr(state, key, default)
```

This skeleton is illustrative; the implementation must match `docs/standards/logging-standards.md` exactly when the two diverge.

---

## Appendix C — Logging field reference and example records

Required fields on every record:

- `timestamp` — ISO-8601 UTC with millisecond precision, suffix `Z`
- `level` — `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`
- `logger` — dotted logger name (`pipelines.workflows.image_prompt_gen.run`)
- `event` — short `snake_case` event name
- `workflow` — `image_prompt_gen` | `template_upload` | `shared`
- `run_id` — opaque run identifier or `null`
- `message` — human-readable summary

Optional, promoted to top level when present: `node`, `component`, `duration_ms`, `error.code`, `error.message`, `error.retryable`.

Free-form workflow-specific fields nest under `extra`.

Example node-emitted record:

```json
{"timestamp":"2026-04-25T14:02:11.482Z","level":"INFO","logger":"pipelines.workflows.template_upload.nodes.persist","event":"node_completed","workflow":"template_upload","run_id":"r-2026-04-25-001","node":"persist","duration_ms":124,"message":"node_completed","extra":{"rows_written":42}}
```

Example non-node record:

```json
{"timestamp":"2026-04-25T14:02:08.011Z","level":"INFO","logger":"pipelines.run","event":"run_started","workflow":"image_prompt_gen","run_id":"r-2026-04-25-001","message":"run_started","extra":{"input_file":"…/portraits.jsonl"}}
```

Example error record:

```json
{"timestamp":"2026-04-25T14:02:13.991Z","level":"ERROR","logger":"pipelines.workflows.template_upload.nodes.persist","event":"node_failed","workflow":"template_upload","run_id":"r-2026-04-25-001","node":"persist","error.code":"sqlite3.OperationalError","error.message":"database is locked","error.retryable":true,"message":"node_failed"}
```

---

## Appendix D — Compatibility wrapper template

Every legacy `ComicBook/comicbook/<x>.py` module becomes a wrapper during TG2 and is deleted in TG5. Two patterns exist depending on whether the wrapper needs to keep stable test-mock identity.

### Pattern 1 — Symbol re-export (default)

Use this for modules where consumers import names rather than monkey-patching the module:

```python
"""Compatibility wrapper. Removed in TG5."""

from pipelines.shared.config import *  # noqa: F401,F403
from pipelines.shared.config import AppConfig, load_config  # noqa: F401
```

### Pattern 2 — Module alias (when monkey-patching matters)

Some legacy tests monkey-patch attributes on `comicbook.run` directly (for example replacing `comicbook.run.build_runtime_deps`). In that case, alias the module rather than re-exporting symbols:

```python
"""Compatibility wrapper. Removed in TG5."""

import sys

from pipelines.workflows.image_prompt_gen import run as _real

sys.modules[__name__] = _real
```

The TG2 test in `workflows/tests/shared/test_compat_*.py` must assert `comicbook.run is pipelines.workflows.image_prompt_gen.run` for any module that uses Pattern 2.

### `workflows/comicbook/nodes/__init__.py`

```python
"""Compatibility wrapper subpackage. Removed in TG5."""
```

(plus per-node wrapper files that follow Pattern 1 and additionally re-export the legacy `upload_*` callable name where applicable.)

---

## Appendix E — `workflows/pyproject.toml` template

Use as a starting point for TG2.T1; preserve the original `ComicBook/pyproject.toml` dependency list verbatim. Replace `…` with values copied from the legacy file.

```toml
[project]
name = "pipelines"
version = "…"
description = "LangGraph workflows for image prompt generation and template upload"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    # copy verbatim from ComicBook/pyproject.toml
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["pipelines*", "comicbook*"]   # comicbook* removed in TG5

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-q"

[tool.ruff]
# copy verbatim from ComicBook/pyproject.toml if present

[tool.mypy]
# copy verbatim from ComicBook/pyproject.toml if present
```

---

## Appendix F — Doc-slug rename checklist (TG2.T10)

The image-workflow planning slug used a mixed-case legacy folder name when this guide was authored. Run all three moves and refresh every link.

```bash
git mv docs/planning/<mixed-case-image-workflow-folder> docs/planning/image-prompt-gen-workflow
git mv docs/business/<mixed-case-image-workflow-folder> docs/business/image-prompt-gen-workflow  # if it exists with that case
git mv docs/developer/<mixed-case-image-workflow-folder> docs/developer/image-prompt-gen-workflow  # if it exists with that case

grep -RIn '<old-mixed-case-image-workflow-slug>' .   # should be empty after fixes
```

Files that commonly link the old slug: `docs/planning/index.md`, `docs/business/index.md`, `docs/developer/index.md`, the per-tree workflow indexes, `AGENTS.md`, `.opencode/agents/*.md`, `docs/standards/repo-structure.md` (only if it lists the slug literally — the canonical mapping table is already correct).
