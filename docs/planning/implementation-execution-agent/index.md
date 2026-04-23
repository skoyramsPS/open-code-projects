# Implementation Execution Agent

Planning documentation for the repository's implementation execution workflow.

## Purpose

This workflow adds a dedicated implementation agent that executes repository implementation guides in small, resumable delivery slices.

The agent is designed to do real build work, not just restate plans. Each run should complete one commit-sized slice of an implementation guide, including testing, documentation updates, and handoff status maintenance.

## Goals

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

### Main agent

`implementation-agent` lives in `.opencode/agents/implementation-agent.md`.

It is responsible for:

- reading the implementation guide and current repo state
- choosing the next eligible slice
- implementing the selected slice
- running tests
- updating docs when needed
- updating the handoff file before stopping

### Reused existing skills

The agent reuses existing repo-local skills instead of duplicating their policies.

- `pytest-tdd-guard` for Python behavior changes, bug fixes, and risky refactors
- `docs-update-guard` for significant documentation updates
- `workflow-readiness-check` when a final readiness review is needed

### New reusable skills

Two new skills were added because the current repo did not already define reusable guidance for implementation slicing or handoff maintenance.

- `implementation-slice-guard`: selects the next commit-sized slice from an implementation guide and handoff record
- `implementation-handoff-guard`: creates and updates the planning-folder handoff record used to resume work later

### Invocation path

`/implement-next <implementation-doc> [handoff-doc]`

The command defaults the handoff path to `implementation-handoff.md` beside the implementation guide.

## Slice-selection policy

The implementation guide's TaskGroup order remains authoritative.

The agent should:

1. find the first unfinished TaskGroup whose dependencies are satisfied
2. determine whether the remaining work in that TaskGroup is small and cohesive enough for one commit
3. if yes, complete the whole TaskGroup
4. if not, complete one task or one inseparable cluster of adjacent tasks from that TaskGroup

The commit-sized rule is intentional. It reduces long-lived partial work and aligns implementation progress with reviewable, test-backed increments.

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

- the repo contains a callable `implementation-agent`
- the repo contains reusable slice-selection and handoff-maintenance skills
- a command exists for invoking the agent against an implementation guide
- the current `Image-prompt-gen-workflow` planning folder contains an initial handoff file
- docs explain what the workflow is, how to use it, and how status resumes across sessions
- the ADR record explains why the repository adopted this workflow
