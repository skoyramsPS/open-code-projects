# ADR-0002: Reorganize the repository into a multi-workflow `pipelines` package with a shared logging standard

- Status: Accepted
- Date: 2026-04-24
- Owners: Repository maintainers

## Context

The repository currently ships two LangGraph workflows inside one flat package (`ComicBook/comicbook`):

- the image-prompt-generation workflow (`graph.py` + `run.py`)
- the template-upload workflow (`upload_graph.py` + `upload_run.py`)

All nodes for both workflows live flat in `comicbook/nodes/`, distinguished only by an `upload_` prefix. Workflow-specific code (router prompts, image client, pricing) lives next to cross-cutting infrastructure (`db.py`, `config.py`, `deps.py`, `execution.py`). State models for both workflows are mixed in one `state.py`. Logging is implicit: a single logger is constructed in `runtime_deps.py`, only the CLI module emits log lines, and nodes do not log structured events at all. Documentation slugs are inconsistent across the planning, business, and developer trees, and `docs/standards/repo-structure.md` describes a per-workflow layout the code does not actually follow.

The cost of this drift compounds as more workflows are added: every new workflow either inherits the convention of pooling everything at the root, or invents its own conflicting structure. There is also no shared way to filter logs by workflow or by run, which makes multi-workflow operations harder to debug.

## Decision

Adopt a per-workflow subpackage layout under a new top-level `workflows/` folder, with one shared subpackage and a single shared logging module.

Concrete commitments:

1. Rename top folder `ComicBook/` → `workflows/`. Rename the importable Python package `comicbook` → `pipelines`. Workflow names stay descriptive of their function: `image_prompt_gen` and `template_upload`.
2. Inside `pipelines/`, split code into `pipelines/shared/` (cross-workflow infrastructure) and `pipelines/workflows/<workflow>/` (workflow-owned code, including its `nodes/`, `prompts/`, `adapters/`, `state.py`, `graph.py`, `run.py`).
3. Treat every node, adapter, and helper as reusable in principle. The folder it lives in records its current ownership, not exclusivity. When a second workflow imports a module, that module is promoted into `pipelines/shared/`.
4. Split state schemas: shared types in `pipelines/shared/state.py`; per-workflow types in each workflow's `state.py`. No model is duplicated.
5. Adopt a single logging standard: structured JSON via stdlib only, with one shared module (`pipelines/shared/logging.py`) used by every workflow, node, and shared module. Nodes log through `log_node_event(deps, state, event, **fields)`; non-node code uses `get_logger(__name__)` with the `log_event(...)` wrapper. Required fields: `timestamp`, `level`, `logger`, `event`, `workflow`, `run_id`, `message`. Full specification in `docs/standards/logging-standards.md`.
6. Normalize doc-tree slugs to lowercase-hyphenated form ending in `-workflow` (`image-prompt-gen-workflow`, `template-upload-workflow`). Record the Python-module-to-doc-slug mapping in `docs/standards/repo-structure.md`.
7. Keep `AGENTS.md` and every `.opencode/agents/*.md` synchronized with the new layout, the logging gate, and the slug mapping. Future significant changes must update these files in the same gate that updates the documentation triad.
8. Execute the migration in five phases: (1) shared logging module, (2) directory moves with import shims, (3) state split, (4) node logging adoption, (5) cleanup. Each phase is one implementation-guide pass with its own handoff. The current round delivers planning and standards only.

## Consequences

Positive:

- Adding a third workflow becomes a copy of one folder under `pipelines/workflows/` with no risk to either existing workflow.
- Every log line is filterable by `workflow` and `run_id` regardless of source. Operators can correlate cross-workflow activity.
- The mapping between code modules, documentation slugs, and ADRs is explicit and one-to-one, so changes do not silently desynchronize.
- Reuse becomes a first-class concept rather than implicit; promotion to `shared/` is a planned move with a single, obvious destination.

Negative or accepted costs:

- Phase 2 changes every import. A temporary `comicbook` shim absorbs the disruption for external scripts but is itself code that has to be removed in Phase 5.
- The pricing JSON, router prompts, and image client are demonstrably image-workflow-only today. If a future workflow needs them, they have to be promoted into `shared/`, which is one more change than leaving them at the root would have been.
- The logging standard requires every node touched in Phase 4 to be edited, even if its behavior is unchanged. Mitigated by phase isolation and additive logging-only tests.

## Alternatives considered

- **Keep the flat layout, just rename for symmetry.** Rejected: it does not solve the mixed shared/workflow concerns and does not enforce reuse boundaries.
- **All state in `shared/state.py`.** Rejected: it preserves the pattern that produced today's blurred boundaries.
- **structlog instead of stdlib JSON.** Rejected for now: stdlib meets every required field with no new runtime dependency. Reconsider if context-binding ergonomics become a recurring pain.
- **Big-bang single-PR reorganization.** Rejected: harder to bisect failures, harder to keep tests green during the move, and tightly couples logging adoption to directory moves.

## Compliance and follow-up

- `docs/standards/repo-structure.md` is updated to describe the target layout and the slug mapping.
- `docs/standards/logging-standards.md` is added and listed in the standards index.
- `opencode.json` loads the new logging standard.
- `AGENTS.md` and every `.opencode/agents/*.md` reference the new layout and the logging gate.
- This ADR was updated to **Accepted** when TG1 landed and will move to **Accepted and Implemented** at the end of Phase 5.
