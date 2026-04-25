# Implementation Execution Agent

Plain-language documentation for the implementation execution workflow.

## What it is

The implementation execution workflow is the repository's delivery worker for approved implementation guides.

Instead of taking on an entire implementation document in one pass, it advances the work in small, controlled slices. Each completed slice should leave behind working progress, tests, updated documentation, and a handoff note that tells the next session exactly where to continue.

## When to use it

Use this workflow when a planning folder already contains an `implementation.md` file and the team wants OpenCode to start building against that document.

Use `/implementation-doc` first when the planning folder only has a design or plan doc and still needs a standalone implementation guide plus a seeded handoff.

If the plan still leaves important technical questions open, the guide-writing step should pause and ask those questions before it writes the implementation guide. The goal is to reduce implementation churn, not to force developers to guess.

Typical use:

- the plan is approved
- the implementation guide is detailed enough to execute, with clear TaskGroup scope and little room for assumptions
- the team wants progress in reviewable increments instead of one large batch

## Modes

The workflow now supports two execution styles:

- `/implement-next`: completes one slice, updates the handoff, and stops for another approval.
- `/implement-next-autonomous`: starts from the same kind of approved implementation guide, but keeps moving through later slices in the same run until the work is done or a protected action needs approval.

## What to expect from each run

Each implementation run should:

- pick the next unfinished part of the implementation guide
- keep the scope small enough to fit one coherent commit
- build and test the selected slice
- update any required docs
- update the handoff file in the same planning folder

When the workflow is used correctly, the guide-creation step and the build step are separate:

- `/implementation-doc` first asks clarifying questions if the plan is still ambiguous, then creates the implementation guide and handoff once those answers are known, then stops
- the handoff asks the user for permission before `/implement-next` starts coding
- the same initial approval rule also applies before `/implement-next-autonomous` starts coding
- generic wording such as `continue` or `go ahead` is not enough to start coding after `/implementation-doc`
- the next coding step should start only after someone explicitly approves `/implement-next` or `/implement-next-autonomous`
- `/implement-next` completes one slice and then asks again before any further slice continues
- `/implement-next-autonomous` keeps honoring the guide slice by slice, but auto-approves later handoff checkpoints until it hits a protected action or finishes the guide

## Approval expectations

Most normal implementation work now runs without extra approval prompts.

- reading repository files and inspecting git state is automatic
- running tests is automatic
- `uv run` pytest commands and simple local version checks are automatic
- normal implementation edits and planned file moves are automatic
- installing packages, deleting files, copying files, or pushing remote git state still pauses for approval

This keeps routine delivery work moving while preserving explicit approval for higher-risk or less easily reversible operations.

## Why the handoff file matters

The handoff file prevents lost context between sessions.

It tells the next run:

- what is already done
- what was tested
- what changed in docs
- what is still blocked
- what should be implemented next
- whether the user has approved the next implementation step yet

This makes the workflow safer to pause and resume without relying on memory.

## What a good implementation guide looks like

A good guide should:

- break the work into ordered TaskGroups
- state what each TaskGroup does and does not include
- show the important files, tests, and acceptance checks
- include technical examples or pseudocode when the code shape would otherwise be unclear

That level of detail helps developers make steady progress instead of reopening scope questions during implementation.

## Limits

- it does not replace the implementation guide as the source of design truth
- it does not auto-commit unless a user explicitly asks for a commit
- the autonomous mode does not auto-push; remote git mutations still need approval
- it does not skip required testing or documentation just to move faster
- it should not work ahead on later TaskGroups while earlier dependency work is unfinished
