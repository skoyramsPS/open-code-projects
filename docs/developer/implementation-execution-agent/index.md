# Implementation Execution Agent

Developer documentation for the repository's implementation execution workflow.

## Files added for this workflow

- `.opencode/commands/implementation-doc.md`
- `.opencode/agents/implementation-agent.md`
- `.opencode/commands/implement-next.md`
- `.opencode/skills/implementation-slice-guard/SKILL.md`
- `.opencode/skills/implementation-handoff-guard/SKILL.md`

## How to invoke it

Use:

- `/implementation-doc <planning-doc> [implementation-doc]`
- `/implement-next <implementation-doc> [handoff-doc]`

Examples:

- `/implementation-doc docs/planning/Image-prompt-gen-workflow/input-file-support-design.md`
- `/implement-next docs/planning/Image-prompt-gen-workflow/implementation.md`
- `/implement-next docs/planning/Image-prompt-gen-workflow/implementation.md docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`

If no handoff path is provided, the workflow uses `implementation-handoff.md` beside the implementation guide.

Expected control flow:

1. `/implementation-doc` creates the execution guide and seeds the handoff file.
2. `/implementation-doc` stops and asks the user whether to proceed.
3. `/implement-next` executes one slice only after that explicit approval, which must explicitly name `/implement-next`.
4. `/implement-next` updates the handoff and asks again before any later slice.

Generic continuation wording such as `continue`, `go ahead`, `keep going`, `continue with your task`, or `summarize and continue` is not sufficient approval for the first implementation slice.

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

## Permission posture

The implementation agent now carries a more granular approval policy.

- `read`, `glob`, and `grep` are auto-approved
- safe git inspection commands such as `git status`, `git diff`, `git log`, `git show`, `git rev-parse`, `git branch`, `git ls-files`, and `git remote` are auto-approved
- pytest execution commands are auto-approved
- `mkdir` and `mv` are auto-approved when used to carry out the selected implementation slice
- file creation and edits are auto-approved through the agent's `edit` permission
- package installation commands remain approval-gated
- copy commands remain approval-gated
- delete commands remain approval-gated

Important limitation: OpenCode's `edit` permission is path-based, so it can distinguish where edits happen but not whether a particular edit is a create, modify, move, or delete. The workflow therefore enforces the "ask before delete" rule in both the agent prompt and the implementation command text, in addition to the bash permission rules.

## Skill reuse matrix

Existing skills reused directly:

- `pytest-tdd-guard`
- `docs-update-guard`
- `workflow-readiness-check`

New skills introduced for reuse:

- `implementation-slice-guard`
- `implementation-handoff-guard`

Additional guardrail behavior:

- `implementation-slice-guard` now flags slices that would need install, copy, or delete approval before they can complete
- `implementation-handoff-guard` now records any approval-gated install, copy, or delete work that blocked or remains for the next session
- `pytest-tdd-guard` now states that pytest execution is pre-approved when invoked from this workflow

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
- explicit permission checkpoint before additional implementation proceeds
- a hard-stop marker that makes the approval boundary machine-readable to later sessions
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
