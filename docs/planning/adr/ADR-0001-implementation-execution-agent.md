# ADR-0001: Add an implementation execution agent with a planning-folder handoff ledger

- Status: Accepted
- Date: 2026-04-23
- Owners: OpenCode repository maintainers

## Context

The repository already defines planning, testing, documentation, and workflow-review helpers, but it does not yet define a dedicated agent for carrying an implementation guide through actual execution.

That gap creates three problems:

1. implementation guides can describe ordered TaskGroups, but there is no standard executor that turns them into commit-sized delivery slices
2. progress can become hard to resume across sessions because execution status is not stored beside the implementation guide
3. testing and documentation gates can be applied inconsistently when implementation work is resumed later by a different session

The repo's implementation-guide format already groups delivery work into ordered TaskGroups with dependencies, exit criteria, and handoff notes. The missing piece is a standard execution workflow that respects that structure.

External guidance consulted while shaping this decision reinforced three principles that also match the repo's existing standards:

- keep delivery increments small and reviewable
- include tests with the implementation change
- maintain explicit, checkable status instead of informal progress notes

## Decision

Add a new `implementation-agent` subagent plus two reusable support skills.

The workflow will:

- execute the next eligible slice from an implementation guide
- keep each run scoped to one git-commit-sized unit of work
- complete an entire TaskGroup only when the remaining work is small and cohesive enough for one session
- otherwise complete one task or one inseparable task cluster from the next eligible TaskGroup
- reuse `pytest-tdd-guard` and `docs-update-guard` instead of duplicating their policies
- maintain an `implementation-handoff.md` file in the same planning folder as the implementation guide so the next session can resume from explicit status
- auto-approve read-only inspection, safe git read/get commands, tests, and normal in-slice edits or moves
- require approval for package installation, copy operations, and delete operations

The repository will also expose `/implement-next <implementation-doc> [handoff-doc]` as the normal invocation path.

## Alternatives considered

### Keep using only ad hoc implementation prompts

Rejected because execution scope, testing expectations, and resume state would remain inconsistent across sessions.

### Build one large implementation agent with no reusable skills

Rejected because slice-selection and handoff maintenance are reusable behaviors that should not be trapped inside a single agent definition.

### Use the implementation guide itself as both plan and status ledger

Rejected because it mixes stable execution instructions with ephemeral session status, making the authoritative guide noisier and harder to maintain.

## Consequences

Benefits:

- implementation work now has a standard executor aligned with the repository's implementation-guide format
- progress can resume from a planning-folder handoff ledger instead of rediscovery
- testing and documentation expectations are baked into each delivery slice
- slice-selection and handoff rules are reusable in future workflows
- the workflow moves faster on routine implementation steps without auto-approving higher-risk install, copy, or delete operations

Tradeoffs and costs:

- each implementation workflow now carries an extra handoff document that must be maintained
- there is a small amount of process overhead at the end of each session
- agent authors must keep the handoff doc and implementation guide clearly separated in purpose

Follow-up work:

- create the first real implementation sessions using `/implement-next`
- keep workflow-specific handoff files current as execution begins

## Related docs

- `docs/planning/implementation-execution-agent/index.md`
- `docs/business/implementation-execution-agent/index.md`
- `docs/developer/implementation-execution-agent/index.md`
- `docs/planning/Image-prompt-gen-workflow/implementation.md`
- `docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`
