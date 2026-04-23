# AGENTS.md

This repository uses OpenCode with Python-first rules for building modular, reusable LangGraph workflows.

Keep this file concise. Put durable standards in `opencode.json` instruction files under `docs/standards/`, and keep those files current.

## Default operating contract

- Use Python for workflow and support code unless a directory already establishes a stronger local rule.
- Build LangGraph workflows from small, reusable modules with explicit state contracts and dependency injection.
- Treat significant changes as gated work: tests and documentation must be updated before the work is complete.
- Use `pytest` as the default test runner and follow TDD when practical.
- Keep architecture decisions auditable. Major workflow or subsystem changes require an ADR in `docs/planning/adr/`.

## Significant-change gate

A change is significant when it does any of the following:

- adds or removes a workflow, node, graph edge, interrupt, persistence boundary, or integration
- changes state schemas, contracts, public interfaces, configuration, or runtime behavior
- changes retry, idempotency, observability, security, or operational behavior
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

If a change is not significant, say so explicitly in the final summary.

## Testing gate

For Python behavior changes, bug fixes, or risky refactors:

1. Load and follow `pytest-tdd-guard`.
2. Add or update tests before declaring the work done.
3. Prefer the smallest failing test first, then the smallest implementation change, then refactor.
4. Run the smallest meaningful pytest scope first, then broaden as confidence grows.

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
- every level keeps an `index.md`
- workflow-specific docs should use the same slug across all three doc trees

## OpenCode layout

- `.opencode/agents/` for project subagents
- `.opencode/commands/` for reusable commands
- `.opencode/skills/` for auto-discovered local skills
- `opencode.json` for shared instruction files and permissions

## Recommended commands

- `/plan-workflow <topic>`
- `/update-docs <topic>`
- `/test-change <topic>`
- `/adr <decision>`
- `/workflow-review <topic>`
