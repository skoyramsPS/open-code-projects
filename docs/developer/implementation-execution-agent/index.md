# Implementation Execution Agent

Developer documentation for the repository's implementation execution workflow.

## Files added for this workflow

- `.opencode/agents/implementation-agent.md`
- `.opencode/commands/implement-next.md`
- `.opencode/skills/implementation-slice-guard/SKILL.md`
- `.opencode/skills/implementation-handoff-guard/SKILL.md`

## How to invoke it

Use:

`/implement-next <implementation-doc> [handoff-doc]`

Examples:

- `/implement-next docs/planning/Image-prompt-gen-workflow/implementation.md`
- `/implement-next docs/planning/Image-prompt-gen-workflow/implementation.md docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`

If no handoff path is provided, the workflow uses `implementation-handoff.md` beside the implementation guide.

## Execution model

The implementation agent is an execution-oriented subagent, not a planning assistant.

Expected sequence:

1. read the implementation guide and current handoff record
2. inspect the relevant codebase state
3. choose the next eligible commit-sized slice
4. implement it end to end
5. run tests
6. update docs if the slice changed behavior or process expectations
7. update the handoff doc with exact resume instructions
8. stop

## Skill reuse matrix

Existing skills reused directly:

- `pytest-tdd-guard`
- `docs-update-guard`
- `workflow-readiness-check`

New skills introduced for reuse:

- `implementation-slice-guard`
- `implementation-handoff-guard`

## Handoff document expectations

The handoff file is the session-to-session execution ledger.

Minimum required content:

- links to the implementation guide and related docs
- TaskGroup status summary
- last completed slice
- files changed in the latest session
- tests run and result
- docs updated
- blockers or open questions
- next recommended slice
- append-only session log

Recommended status values:

- `not started`
- `in progress`
- `completed`
- `blocked`

## Conflict rule

If the handoff file and implementation guide disagree:

- trust the implementation guide for sequencing and technical contracts
- trust repository reality for what is actually implemented
- update the handoff file to reconcile the mismatch before closing the session

## Scope rule

One implementation-agent run should normally map to one coherent commit.

The agent may complete an entire TaskGroup only when the remaining work is small and cohesive enough to be reviewed as a single concern. Otherwise it must stop after one task or one inseparable task cluster from the next eligible TaskGroup.

## Current seeded handoff

The current planning folder `docs/planning/Image-prompt-gen-workflow/` now includes an initial `implementation-handoff.md` file so the first implementation session has a status ledger to resume from.
