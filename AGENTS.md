# AGENTS.md

This repository uses OpenCode with Python-first rules for building modular, reusable LangGraph workflows in a multi-workflow `pipelines` package.

Keep this file concise. Put durable standards in `opencode.json` instruction files under `docs/standards/`, and keep those files current.

## Default operating contract

- Use Python for workflow and support code unless a directory already establishes a stronger local rule.
- Build LangGraph workflows from small, reusable modules with explicit state contracts and dependency injection.
- Treat every node, adapter, and helper as reusable in principle. The folder it lives in records its current ownership, not exclusivity.
- Treat significant changes as gated work: tests, structured logging, and documentation must be updated before the work is complete.
- Use `pytest` as the default test runner and follow TDD when practical.
- Keep architecture decisions auditable. Major workflow or subsystem changes require an ADR in `docs/planning/adr/`.

## Significant-change gate

A change is significant when it does any of the following:

- adds or removes a workflow, node, graph edge, interrupt, persistence boundary, or integration
- changes state schemas, contracts, public interfaces, configuration, or runtime behavior
- changes retry, idempotency, observability (including logging fields), security, or operational behavior
- changes developer setup, testing strategy, deployment/runtime assumptions, or user-visible behavior
- introduces an ADR-worthy tradeoff or architectural decision

For significant changes:

1. Load and follow `docs-update-guard` before marking work complete.
2. Update the documentation triad under `docs/`:
   - `docs/planning/`
   - `docs/business/`
   - `docs/developer/`
3. Update the relevant `index.md` files.
4. Create or update an ADR under `docs/planning/adr/` when the change alters architecture or makes a lasting tradeoff.
5. If the change touches workflow runtime behavior, confirm log lines still meet the [logging standard](docs/standards/logging-standards.md): every emitted record carries `workflow`, `run_id`, `event`, and (when inside a node) `node`.

If a change is not significant, say so explicitly in the final summary.

## Testing gate

For Python behavior changes, bug fixes, or risky refactors:

1. Load and follow `pytest-tdd-guard`.
2. Add or update tests before declaring the work done.
3. Prefer the smallest failing test first, then the smallest implementation change, then refactor.
4. Run the smallest meaningful pytest scope first, then broaden as confidence grows.

## Logging gate

For any change that adds, edits, or moves a node, adapter, graph, run module, or shared infrastructure module:

- nodes log only through `log_node_event(deps, state, event, **fields)` from `pipelines.shared.logging`
- non-node code uses `get_logger(__name__)` and the `log_event(...)` helper from the same module
- every log line includes the required fields defined in [`docs/standards/logging-standards.md`](docs/standards/logging-standards.md)
- redaction flags such as `redact_prompts` and `redact_style_text_in_logs` are honored in any new log site

## Workflow quality gate

For workflow planning, implementation review, or final readiness checks:

- use `langgraph-architect` for architecture and graph design work
- use `test-engineer` for test strategy, pytest coverage, and regression checks
- use `docs-writer` for the documentation triad, indexes, and ADR maintenance
- load `workflow-readiness-check` before claiming a significant workflow change is ready to ship

## Documentation model

All project documentation lives under `docs/`.

- `docs/planning/` contains planning and implementation material
- `docs/business/` contains non-technical documentation
- `docs/developer/` contains maintainer documentation
- `docs/standards/` holds the standards loaded by `opencode.json`
- every level keeps an `index.md`
- workflow-specific docs use the same slug across all three doc trees, lowercase-hyphenated and ending in `-workflow`
- the Python-module-to-doc-slug mapping is recorded in [`docs/standards/repo-structure.md`](docs/standards/repo-structure.md)

Current workflow slugs:

| Python module under `pipelines.workflows.` | Doc slug |
| --- | --- |
| `image_prompt_gen` | `image-prompt-gen-workflow` |
| `template_upload` | `template-upload-workflow` |

## Repository layout

The runtime code lives in the `pipelines` package under the top-level `workflows/` folder:

```
.
├── AGENTS.md
├── opencode.json
├── .opencode/
├── docs/
└── workflows/
    └── pipelines/
        ├── shared/                # cross-workflow infrastructure
        │   ├── config.py
        │   ├── deps.py
        │   ├── runtime_deps.py
        │   ├── execution.py
        │   ├── db.py
        │   ├── fingerprint.py
        │   ├── responses.py
        │   ├── metadata_backfill.py
        │   ├── repo_protection.py
        │   ├── logging.py
        │   └── state.py
        └── workflows/
            ├── image_prompt_gen/  # image prompt generation workflow
            │   ├── graph.py
            │   ├── run.py
            │   ├── state.py
            │   ├── pricing.json
            │   ├── prompts/
            │   ├── adapters/
            │   └── nodes/
            └── template_upload/   # template upload workflow
                ├── graph.py
                ├── run.py
                ├── state.py
                └── nodes/
```

This layout is now the implemented repository baseline. Historical migration details live under [`docs/planning/repo-reorganization/`](docs/planning/repo-reorganization/).

## OpenCode layout

- `.opencode/agents/` for project subagents
- `.opencode/commands/` for reusable commands
- `.opencode/skills/` for auto-discovered local skills
- `opencode.json` for shared instruction files and permissions

## Recommended commands

- `/plan-workflow <topic>`
- `/implementation-doc <planning-doc> [output-doc]`
- `/implement-next <implementation-doc> [handoff-doc]`
- `/implement-next-autonomous <implementation-doc> [handoff-doc]`
- `/update-docs <topic>`
- `/test-change <topic>`
- `/adr <decision>`
- `/workflow-review <topic>`
