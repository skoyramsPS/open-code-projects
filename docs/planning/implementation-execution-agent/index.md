# Implementation Execution Agent

Planning documentation for the repository's implementation execution workflow.

## Purpose

This workflow adds dedicated implementation agents that execute repository implementation guides in small, resumable delivery slices.

The agents are designed to do real build work, not just restate plans. The standard agent stops after one commit-sized slice. The autonomous variant keeps chaining commit-sized slices until the guide is complete or an approval-gated action blocks progress.

The guide-authoring step is intentionally clarification-gated: if the planning material leaves implementation-critical ambiguity, `/implementation-doc` should ask the user questions first and only write the implementation guide once those answers are locked.

## Goals

- create implementation guides and stop with a resumable handoff before any coding starts
- execute implementation guides directly from `docs/planning/.../implementation.md`
- keep each run scoped to one coherent git-commit-sized slice
- default to the next unfinished TaskGroup, but split it when a full TaskGroup would be too large for one session
- run verification in the same session as the implementation change
- update relevant documentation before the slice is considered complete
- maintain a planning-folder handoff document so the next session can resume without re-deriving status

## Non-goals

- replacing planning docs as the source of design and sequencing authority
- auto-committing or auto-pushing changes without a user request
- finishing multiple unrelated TaskGroups in one session
- using handoff notes as a substitute for tests or repository documentation

## Design summary

### Implementation-guide quality bar

`/implementation-doc` is expected to produce a delivery-grade technical guide, not a broad prose summary.

Before the guide is written or materially revised, the docs workflow should inspect the planning doc, related docs, and relevant repository state closely enough to surface any ambiguity that would change:

- TaskGroup scope or ordering
- file or module ownership
- public/runtime contracts
- testing expectations
- observability or logging requirements
- acceptance criteria or rollout behavior

If any such ambiguity remains, the workflow should stop and ask the user for clarification before writing the guide. Multiple clarification rounds are valid and expected when needed.

Every implementation guide should organize work into ordered `TaskGroup`s. Each `TaskGroup` should be specific enough that an implementation agent can execute it without guessing. At minimum, each `TaskGroup` must include:

- goal
- dependencies
- exact in-scope work
- exact out-of-scope work
- deterministic task list
- expected files or modules
- tests and verification steps
- documentation and observability impact
- exit criteria
- handoff notes for the next TaskGroup

When a `TaskGroup` includes code changes, refactors, or new modules/APIs, the guide should also provide representative pseudocode, code skeletons, or concrete snippets for the non-obvious implementation patterns.

### Main agents

`implementation-agent` lives in `.opencode/agents/implementation-agent.md`.

`autonomous-implementation-agent` lives in `.opencode/agents/autonomous-implementation-agent.md`.

The standard agent is responsible for:

- reading the implementation guide and current repo state
- choosing the next eligible slice
- implementing the selected slice
- running tests
- updating docs when needed
- updating the handoff file before stopping

The autonomous variant keeps the same slice-selection and handoff discipline, but changes the stop rule:

- it still works one commit-sized slice at a time
- it updates the handoff after every completed slice
- it auto-approves later handoff checkpoints within the same run
- it stops only when the guide is complete or a gated action, blocker, or unresolved question requires user input

### Reused existing skills

The agents reuse existing repo-local skills instead of duplicating their policies.

- `pytest-tdd-guard` for Python behavior changes, bug fixes, and risky refactors
- `docs-update-guard` for significant documentation updates
- `workflow-readiness-check` when a final readiness review is needed

### New reusable skills

Two new skills were added because the current repo did not already define reusable guidance for implementation slicing or handoff maintenance.

- `implementation-slice-guard`: selects the next commit-sized slice from an implementation guide and handoff record
- `implementation-handoff-guard`: creates and updates the planning-folder handoff record used to resume work later

### Invocation path

`/implementation-doc <planning-doc> [implementation-doc]`

`/implement-next <implementation-doc> [handoff-doc]`

`/implement-next-autonomous <implementation-doc> [handoff-doc]`

Expected two-step flow:

1. `/implementation-doc` inspects the plan, asks clarification questions first if implementation-critical ambiguity remains, then writes the implementation guide, seeds `implementation-handoff.md`, and stops with a permission request.
2. `/implement-next` executes one commit-sized slice only after the user explicitly approves moving from planning into implementation by invoking `/implement-next ...` or by clearly approving `/implement-next` in a later message.
3. `/implement-next-autonomous` uses the same initial approval boundary, then keeps advancing across later handoff checkpoints within the same run until completion or a gated action blocks it.

Generic continuation wording such as `continue`, `go ahead`, `keep going`, `continue with your task`, or `summarize and continue` is not enough to cross the planning-to-implementation boundary.

Both implementation execution commands default the handoff path to `implementation-handoff.md` beside the implementation guide.

## Permission model

The implementation execution workflow now uses a mixed permission posture.

- read-only repository inspection is auto-approved
- safe git read/get commands are auto-approved
- test execution and loading test-related skills are auto-approved
- `uv run` pytest execution is auto-approved for the selected slice
- local version checks such as `python --version`, `python3 --version`, and `uv --version` are auto-approved
- creating, editing, modifying, and moving files or folders are auto-approved when they are part of the selected implementation slice
- package or module installation requires approval
- delete operations require approval
- copy operations require approval
- `git push` and any git-related remote mutation require approval

OpenCode can enforce most of this directly through the agent permission block. The remaining delete-vs-edit distinction is reinforced in the workflow instructions because edit permissions are path-based rather than operation-type aware.

## Slice-selection policy

The implementation guide's TaskGroup order remains authoritative.

The agents should:

1. find the first unfinished TaskGroup whose dependencies are satisfied
2. determine whether the remaining work in that TaskGroup is small and cohesive enough for one commit
3. if yes, complete the whole TaskGroup
4. if not, complete one task or one inseparable cluster of adjacent tasks from that TaskGroup

The commit-sized rule is intentional. It reduces long-lived partial work and aligns implementation progress with reviewable, test-backed increments.

## Stop behavior

The two execution modes share the same slice-selection rules but differ in how they honor handoff checkpoints.

- `implementation-agent` always stops after one completed slice and asks for another explicit `/implement-next` approval.
- `autonomous-implementation-agent` treats later handoff checkpoints as approved within the same run and keeps going until the guide is complete or a gated action, blocker, or clarification request forces a stop.

## Handoff document contract

Every implementation guide should gain a sibling `implementation-handoff.md` file once execution begins.

The handoff document records:

- TaskGroup status
- what was completed in the last session
- changed files
- tests run and results
- documentation updates
- blockers and open questions
- the next recommended slice
- the explicit user-permission checkpoint before additional implementation continues, or the exact action that still needs approval when the autonomous agent stops on a gated operation

The handoff should also carry an unambiguous hard-stop line so later sessions do not infer approval from generic continuation text.

The implementation guide remains the source of truth for intended order and technical contracts. The handoff doc becomes the source of truth for current implementation status.

## Guidance used while designing this workflow

The design was informed by a few external sources that reinforced the repo's existing standards.

- GitLab merge request workflow guidance favors the smallest meaningful change, tests in the same contribution, and one concern per change.
- GitHub task-tracking guidance favors discrete, checkable work items over informal progress notes.
- Martin Fowler's Ship / Show / Ask article reinforces shipping small, ready increments instead of letting work sprawl across long-lived branches or sessions.

Reference URLs:

- `https://docs.gitlab.com/ee/development/contributing/merge_request_workflow.html`
- `https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/about-tasklists`
- `https://martinfowler.com/articles/ship-show-ask.html`

## Acceptance criteria

This workflow is ready when all of the following are true.

- the repo contains callable `implementation-agent` and `autonomous-implementation-agent` variants
- the repo contains reusable slice-selection and handoff-maintenance skills
- commands exist for invoking the standard and autonomous agents against an implementation guide
- the current `image-prompt-gen-workflow` planning folder contains an initial handoff file
- docs explain what the workflow is, how to use it, and how status resumes across sessions
- the ADR record explains why the repository adopted this workflow
