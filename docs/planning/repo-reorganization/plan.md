# Repository Reorganization Plan

- Status: Draft, awaiting approval
- Owner: Repository maintainers
- Scope: package layout, shared logging, doc-slug normalization, agent instruction updates
- Posture for this round: **plan and docs only**. Code moves are deferred to a follow-up implementation guide.

## Why

Today the repository ships two LangGraph workflows in one flat package:

- the image-prompt-generation workflow (`graph.py`, `run.py`, several router and image-client files)
- the template-upload workflow (`upload_graph.py`, `upload_run.py`, `upload_*` nodes)

They share the package root with cross-cutting infrastructure (`db.py`, `config.py`, `deps.py`, `execution.py`, `fingerprint.py`, `state.py`). Workflow-specific files mix with shared files. State models for both workflows live in one `state.py`. Logging is implicit: a single logger is built in `runtime_deps.py`, only the CLI entry point uses it, and nodes do not emit structured events at all. The `docs/standards/repo-structure.md` already describes a per-workflow layout that the actual code does not follow, and the workflow doc slugs were inconsistent before the TG2 normalization.

The reorganization pursues four outcomes:

1. **Clean per-workflow boundaries** — each workflow owns its graph, nodes, prompts, adapters, and state. A third workflow can be added without touching the others.
2. **Reusable shared layer** — every node, adapter, and helper is reusable in principle. Anything used by two or more workflows lives in `shared/` so it is reachable without crossing workflow boundaries.
3. **One logging standard** — every workflow, node, and shared module logs structured JSON through a single shared module with consistent fields (`workflow`, `run_id`, `node`, `event`).
4. **Always-current docs and agent instructions** — repo-structure, AGENTS.md, and every `.opencode/agents/*.md` describe the current shape and gate documentation updates as part of significant changes.

## Decisions locked from clarification

- Per-workflow subpackages **plus** a shared subpackage. All nodes are considered shared in principle; the directory location signals current ownership, not exclusivity.
- Top-level folder rename: `ComicBook/` → `workflows/`. Python package rename: `comicbook` → `pipelines`.
- Workflow slugs in code: `image_prompt_gen`, `template_upload`. Doc slugs: `image-prompt-gen-workflow`, `template-upload-workflow`. Mapping is recorded in `docs/standards/repo-structure.md`.
- State split: `pipelines/shared/state.py` for cross-workflow types; per-workflow `state.py` for workflow-specific types.
- Logging: structured JSON via stdlib only, with a single `pipelines/shared/logging.py` module. Nodes use a `log_node_event(deps, state, event, **fields)` helper; non-node code uses `get_logger(__name__)` and the `log_event(...)` convenience wrapper.
- Execution posture for this round: docs and standards only. Code moves are deferred.

## Target layout

See `docs/standards/repo-structure.md` for the canonical tree. Summary:

```
.
├── AGENTS.md
├── opencode.json
├── .opencode/
├── docs/
└── workflows/
    ├── pipelines/
    │   ├── shared/
    │   │   ├── config.py
    │   │   ├── deps.py
    │   │   ├── runtime_deps.py
    │   │   ├── execution.py
    │   │   ├── db.py
    │   │   ├── fingerprint.py
    │   │   ├── repo_protection.py
    │   │   ├── logging.py
    │   │   └── state.py
    │   └── workflows/
    │       ├── image_prompt_gen/
    │       │   ├── graph.py
    │       │   ├── run.py
    │       │   ├── state.py
    │       │   ├── pricing.json
    │       │   ├── prompts/
    │       │   ├── adapters/
    │       │   └── nodes/
    │       └── template_upload/
    │           ├── graph.py
    │           ├── run.py
    │           ├── state.py
    │           └── nodes/
    └── tests/
        ├── shared/
        ├── image_prompt_gen/
        ├── template_upload/
        └── integration/
```

## Module migration mapping

| Today | After reorganization |
| --- | --- |
| `ComicBook/comicbook/__init__.py` | `workflows/pipelines/__init__.py` |
| `ComicBook/comicbook/config.py` | `workflows/pipelines/shared/config.py` |
| `ComicBook/comicbook/deps.py` | `workflows/pipelines/shared/deps.py` |
| `ComicBook/comicbook/runtime_deps.py` | `workflows/pipelines/shared/runtime_deps.py` |
| `ComicBook/comicbook/execution.py` | `workflows/pipelines/shared/execution.py` |
| `ComicBook/comicbook/db.py` | `workflows/pipelines/shared/db.py` |
| `ComicBook/comicbook/fingerprint.py` | `workflows/pipelines/shared/fingerprint.py` |
| `ComicBook/comicbook/repo_protection.py` | `workflows/pipelines/shared/repo_protection.py` |
| `ComicBook/comicbook/state.py` (shared half) | `workflows/pipelines/shared/state.py` |
| `ComicBook/comicbook/state.py` (image-workflow half) | `workflows/pipelines/workflows/image_prompt_gen/state.py` |
| `ComicBook/comicbook/state.py` (`ImportRunState` etc.) | `workflows/pipelines/workflows/template_upload/state.py` |
| `ComicBook/comicbook/graph.py` | `workflows/pipelines/workflows/image_prompt_gen/graph.py` |
| `ComicBook/comicbook/run.py` | `workflows/pipelines/workflows/image_prompt_gen/run.py` |
| `ComicBook/comicbook/router_llm.py` | `workflows/pipelines/workflows/image_prompt_gen/adapters/router_llm.py` |
| `ComicBook/comicbook/router_prompts.py` | `workflows/pipelines/workflows/image_prompt_gen/prompts/router_prompts.py` |
| `ComicBook/comicbook/metadata_prompts.py` | `workflows/pipelines/workflows/image_prompt_gen/prompts/metadata_prompts.py` |
| `ComicBook/comicbook/image_client.py` | `workflows/pipelines/workflows/image_prompt_gen/adapters/image_client.py` |
| `ComicBook/comicbook/pricing.json` | `workflows/pipelines/workflows/image_prompt_gen/pricing.json` |
| `ComicBook/comicbook/input_file.py` | `workflows/pipelines/workflows/image_prompt_gen/input_file.py` |
| `ComicBook/comicbook/nodes/cache_lookup.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/cache_lookup.py` |
| `ComicBook/comicbook/nodes/generate_images_serial.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/generate_images_serial.py` |
| `ComicBook/comicbook/nodes/ingest.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/ingest.py` |
| `ComicBook/comicbook/nodes/load_templates.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/load_templates.py` |
| `ComicBook/comicbook/nodes/persist_template.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/persist_template.py` |
| `ComicBook/comicbook/nodes/router.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/router.py` |
| `ComicBook/comicbook/nodes/summarize.py` | `workflows/pipelines/workflows/image_prompt_gen/nodes/summarize.py` |
| `ComicBook/comicbook/upload_graph.py` | `workflows/pipelines/workflows/template_upload/graph.py` |
| `ComicBook/comicbook/upload_run.py` | `workflows/pipelines/workflows/template_upload/run.py` |
| `ComicBook/comicbook/nodes/upload_load_file.py` | `workflows/pipelines/workflows/template_upload/nodes/load_file.py` |
| `ComicBook/comicbook/nodes/upload_parse_and_validate.py` | `workflows/pipelines/workflows/template_upload/nodes/parse_and_validate.py` |
| `ComicBook/comicbook/nodes/upload_resume_filter.py` | `workflows/pipelines/workflows/template_upload/nodes/resume_filter.py` |
| `ComicBook/comicbook/nodes/upload_backfill_metadata.py` | `workflows/pipelines/workflows/template_upload/nodes/backfill_metadata.py` |
| `ComicBook/comicbook/nodes/upload_decide_write_mode.py` | `workflows/pipelines/workflows/template_upload/nodes/decide_write_mode.py` |
| `ComicBook/comicbook/nodes/upload_persist.py` | `workflows/pipelines/workflows/template_upload/nodes/persist.py` |
| `ComicBook/comicbook/nodes/upload_summarize.py` | `workflows/pipelines/workflows/template_upload/nodes/summarize.py` |
| `ComicBook/examples/` | `workflows/examples/` |
| `ComicBook/tests/test_*` | `workflows/tests/<workflow_or_shared>/test_*` |
| `ComicBook/DoNotChange/` | `workflows/DoNotChange/` (path stays out of the package; protection check updated) |

Renames also drop the redundant `upload_` function-name prefix inside template-upload nodes once their directory establishes scope.

## State split rules

`pipelines/shared/state.py` contains:

- `WorkflowError`
- `UsageTotals`
- `RunSummary`
- status literals shared between workflows (`RunStatus`, status helpers used by reporting)
- the `WorkflowModel` base class

`pipelines/workflows/image_prompt_gen/state.py` contains:

- `RunState` TypedDict
- `TemplateSummary`, `NewTemplateDraft`, `PromptPlanItem`, `RouterTemplateDecision`, `RouterPlan`, `RenderedPrompt`, `ImageResult`
- image-workflow-only literals (`ImageSize`, `ImageQuality`, `RouterModel`, `ImageResultStatus`)

`pipelines/workflows/template_upload/state.py` contains:

- `ImportRunState` TypedDict
- `TemplateImportRow`, `TemplateImportRowResult`
- `ImportRowStatus`, `ImportWriteMode`

Each workflow `state.py` imports its shared base types from `pipelines.shared.state`. No model is duplicated across files.

## Logging module

The shared module is specified in `docs/standards/logging-standards.md`. The implementation lands under `workflows/pipelines/shared/logging.py` and exposes:

- `get_logger(name) -> logging.Logger`
- `JsonFormatter`
- `NodeLogContext`
- `log_node_event(deps, state, event, *, level="INFO", message=None, **fields)`
- `log_event(logger, event, *, workflow="shared", run_id=None, **fields)`

`Deps.logger` continues to be the injection point. `runtime_deps.py` switches to `get_logger("pipelines.run")` and adopts the shared formatter. CLI entry points call `log_event(...)` instead of `logger.info(...)` so output stays uniform.

A starter implementation is committed in this round so the standard has a concrete reference; full adoption (rewriting every node to use `log_node_event`) happens in the code-migration phases.

## Phased execution (deferred)

This round commits **only** plans, standards, and the logging-module stub. The code migration proceeds later in five phases. Each phase is one implementation-guide pass with its own handoff.

**Phase 1 — Foundations**
- Create the `workflows/pipelines/shared/logging.py` module per the standard.
- Add unit tests for `JsonFormatter`, `log_node_event`, `log_event`.
- Wire `runtime_deps.py` and the two CLI entry points to use the new logger but keep their current package locations.
- No file moves yet. Exit when logging is structured everywhere it currently runs.

**Phase 2 — Directory move with import shims**
- Move files according to the migration mapping above using `git mv` so history is preserved.
- Rename the package `comicbook` → `pipelines` and the top folder `ComicBook` → `workflows`.
- Add a `comicbook/__init__.py` shim (or an editable-install alias) that re-exports the new locations so any external scripts keep working through Phase 4.
- Update `pyproject.toml`, the pre-commit config, the `DoNotChange` protection path, the test-runner command, and `.env.example` paths.
- Update docs path references.
- Exit when `pytest -q` passes from `workflows/`.

**Phase 3 — State split**
- Split `state.py` into `shared/state.py`, `image_prompt_gen/state.py`, and `template_upload/state.py` per the rules above.
- Update every node, graph, run module, and test import to point at the new state homes.
- Exit when `pytest -q` passes and no module imports state from the wrong workflow.

**Phase 4 — Node logging adoption**
- Replace any direct `deps.logger.*` and `logging.getLogger(...)` calls inside nodes with `log_node_event(...)`.
- Add the standard fields (`workflow`, `run_id`, `node`, `event`) on every emitted line.
- Add logging-only tests where coverage is missing.
- Drop redundant `upload_` prefixes inside template-upload node functions and module names; update imports accordingly.
- Exit when log output for a sample run of each workflow is auditable using only the standard fields.

**Phase 5 — Cleanup**
- Remove the `comicbook` shim and any compatibility re-exports.
- Sweep docs for any leftover `ComicBook/comicbook/...` paths and update.
- Promote any node, adapter, or helper that has acquired a second importer into `pipelines/shared/`.
- Refresh the documentation triad and ADR-0002 status as Accepted-and-Implemented.
- Exit when no reference to the old paths remains in code, tests, docs, or agent instructions.

## Documentation impact

Every phase carries a `docs-update-guard` pass. Specifically:

- `docs/standards/repo-structure.md` — already updated this round to describe the new layout and slug mapping.
- `docs/standards/logging-standards.md` — new file added this round.
- `docs/standards/index.md` — already updated this round to list the logging standard.
- `opencode.json` — already updated this round to load the logging standard.
- `AGENTS.md` — already updated this round to reflect new layout, logging, and slugs.
- `.opencode/agents/*.md` — already updated this round so each subagent's permission posture and priorities reflect the new layout and the logging gate.
- Normalize the image workflow doc-tree slug to `image-prompt-gen-workflow` across `docs/planning/`, `docs/business/`, and `docs/developer/` during Phase 2 because the code-move phase is the natural moment to retitle.
- Per-workflow planning docs are updated at the end of each phase that touches their workflow.
- ADR-0002 records this reorganization decision and is marked Accepted at the end of Phase 5.

## Risks and mitigations

- **Import churn breaks live scripts.** Mitigation: Phase 2 ships a temporary `comicbook` import shim so external scripts keep working until Phase 5.
- **Tests fail across the move.** Mitigation: directory moves use `git mv` and tests run after every phase.
- **Logging adoption regresses run reports.** Mitigation: existing run-report tests stay green through Phase 4; new logging-only tests are additive.
- **DoNotChange protection misfires after rename.** Mitigation: Phase 2 updates `scripts/check_do_not_change.py` and the protection path constant in the same commit as the directory move.

## Open questions

- Should the `examples/` folder live under `workflows/examples/` or under each workflow's `examples/`? Default in the plan is repo-level `workflows/examples/`; revisit when the third workflow lands.
- Should the logging standard require a correlation ID separate from `run_id` for nested calls (e.g. inside `input-file` batch mode)? Default is no; revisit if batch logs become hard to disambiguate.
