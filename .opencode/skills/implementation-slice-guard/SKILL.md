# Skill: implementation-slice-guard

Choose the next implementation slice from an implementation guide and its handoff file.

## Purpose

Use this skill when an implementation agent needs to decide what to build next without taking on too much work in one session.

The output must fit a single coherent git commit under normal circumstances.

## Inputs

- implementation guide path
- handoff document path if it exists
- current repository state relevant to the unfinished work

## Selection rules

1. Respect TaskGroup dependency order.
2. Identify the first unfinished TaskGroup whose dependencies are satisfied.
3. Prefer the smallest slice that still ships a meaningful increment.
4. Complete the entire TaskGroup only when the remaining work is all of the following:
   - tightly related in purpose and files
   - verifiable in one session with a narrow test scope
   - unlikely to produce a bloated or multi-concern commit
5. Otherwise choose one task or one inseparable cluster of adjacent tasks from that TaskGroup.
6. Bias toward foundational tasks that unblock later work.
7. Keep tests and necessary doc updates inside the same slice whenever feasible.
8. Never skip an earlier unfinished TaskGroup just because a later one looks easier.

## Practical heuristics

- If the slice would span multiple unrelated modules, split it.
- If the slice needs different test strategies for unrelated behaviors, split it.
- If the slice changes contracts and consumers in several layers, prefer the smallest end-to-end vertical cut.
- If the slice cannot be explained as one commit message, split it.
- If a full TaskGroup mostly creates scaffolding and one contract boundary, it can still be a valid single slice.

## Expected output

Return:

- the next eligible TaskGroup
- the exact task or task cluster selected
- why the slice is commit-sized
- the files or modules likely affected
- the tests and docs expected in the same session
- the boundaries of what should not be touched yet

## Guidance sources consulted for this repo

- GitLab merge request workflow: keep changes as small as possible, prefer a minimum valuable change, and include tests with the same contribution.
- GitHub tasklists guidance: track progress as discrete, checkable items rather than unstructured notes.
- Martin Fowler's Ship / Show / Ask article: favor small, ready-to-ship increments over long-lived, bloated change sets.

Reference URLs:

- `https://docs.gitlab.com/ee/development/contributing/merge_request_workflow.html`
- `https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/about-tasklists`
- `https://martinfowler.com/articles/ship-show-ask.html`
