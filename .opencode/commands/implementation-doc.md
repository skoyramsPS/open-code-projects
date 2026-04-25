---
description: create a standalone technical implementation guide from a planning doc
agent: docs-writer
---

Create or update a standalone technical implementation guide from the planning document at: `$1`

If `$2` is provided, write the implementation guide there. Otherwise, write `implementation.md` in the same directory as `$1`.

Also create or update a sibling `implementation-handoff.md` next to the implementation guide you write. Seed it from the current repository state and end it with an explicit permission checkpoint that asks the user to approve `/implement-next` before any implementation begins.

Required actions:

1. Inspect the source planning document, the local documentation structure, and any related workflow docs before writing.
   - read-only source-code inspection is pre-approved when needed to keep the implementation guide technically accurate.
   - safe git read/get inspection commands are pre-approved.
2. Produce a self-sufficient technical implementation document for the delivery team that can be used without cross-referencing the planning doc during implementation.
3. Resolve planning ambiguities or contradictions explicitly inside the implementation document instead of leaving them implied.
4. Convert the planned work into isolated implementation tasks grouped into ordered `TaskGroup`s.
5. Make TaskGroups sequential and dependency-aware so each later TaskGroup depends on completion of the earlier ones when that ordering matters.
6. For each TaskGroup, include the goal, dependencies, detailed tasks, expected files or modules, exit criteria, and any handoff notes needed by the next group.
7. Include concrete technical detail covering repository layout, module boundaries, runtime contracts, state/data models, persistence expectations, testing requirements, observability, failure handling, and acceptance criteria when the planning doc supports them.
8. Update any impacted planning indexes when adding or renaming workflow planning documents.
9. Create or update the sibling `implementation-handoff.md` with the current status, TaskGroup table, unresolved assumptions, exact next recommended slice, and an explicit note that implementation must not start until the user grants permission.
10. Summarize what was created or updated and call out any remaining assumptions or unresolved decisions.
11. Stop after the implementation guide, index updates, and handoff updates are complete. Do not edit application code, tests, runtime docs, or examples as part of this command.
12. End with a direct handoff asking the user whether to proceed with `/implement-next <implementation-doc> [handoff-doc]`.
13. End the handoff and the final result with the exact line `USER_APPROVAL_REQUIRED: implementation may start only after explicit /implement-next approval`.
14. Treat generic continuation wording such as `continue`, `go ahead`, `keep going`, `continue with your task`, or `summarize and continue` as insufficient approval. Implementation may begin only after a later user message explicitly invokes `/implement-next <implementation-doc> [handoff-doc]` or clearly says `approve /implement-next ...`.

Permission notes for this command:

- reading repository files (including source code) is pre-approved
- writing/editing markdown files under `docs/planning/` is pre-approved
- do not edit runtime code or tests as part of `/implementation-doc`

Output expectations:

- the implementation doc must be execution-oriented, not just a summary
- the implementation doc must be detailed enough that an implementation team can use it as its primary build document
- prefer the smallest set of document edits that fully satisfies the request
- this command is planning-only and handoff-only; it must not auto-transition into implementation work
- the output must make the hard stop unambiguous to the caller and to any later subagent invocation
