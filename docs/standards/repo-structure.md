# Repository Structure Standards

## OpenCode layout

Use these locations consistently:

- `AGENTS.md` at the repo root
- `opencode.json` at the repo root
- `.opencode/agents/` for project subagents
- `.opencode/commands/` for reusable commands
- `.opencode/skills/` for project-local skills
- `.opencode/tools/` only when built-in tools are insufficient

## Documentation layout

All durable docs live under `docs/`.

- `docs/planning/`
- `docs/business/`
- `docs/developer/`
- `docs/standards/`

Prefer the same workflow slug across all three documentation trees. Example:

- `docs/planning/my-workflow/index.md`
- `docs/business/my-workflow/index.md`
- `docs/developer/my-workflow/index.md`

## Python project layout

Unless the repo already uses a stronger local convention, prefer:

- `src/` or package directory for application code
- `tests/` for automated tests
- clear separation between graph definitions, reusable nodes, adapters, schemas, and config

Example workflow-oriented layout:

- `src/<package>/workflows/`
- `src/<package>/nodes/`
- `src/<package>/adapters/`
- `src/<package>/schemas/`
- `src/<package>/config/`
- `tests/unit/`, `tests/integration/`, `tests/e2e/`

## Naming

- use descriptive, stable workflow slugs
- keep skill names lowercase with hyphens
- keep docs titles human-readable even when paths use slugs
