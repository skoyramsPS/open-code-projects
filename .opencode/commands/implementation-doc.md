---
description: create a standalone technical implementation guide from a planning doc
agent: docs-writer
---

Create or update a standalone technical implementation guide from the planning document at: `$1`

If `$2` is provided, write the implementation guide there. Otherwise, write `implementation.md` in the same directory as `$1`.

Required actions:

1. Inspect the source planning document, the local documentation structure, and any related workflow docs before writing.
2. Produce a self-sufficient technical implementation document for the delivery team that can be used without cross-referencing the planning doc during implementation.
3. Resolve planning ambiguities or contradictions explicitly inside the implementation document instead of leaving them implied.
4. Convert the planned work into isolated implementation tasks grouped into ordered `TaskGroup`s.
5. Make TaskGroups sequential and dependency-aware so each later TaskGroup depends on completion of the earlier ones when that ordering matters.
6. For each TaskGroup, include the goal, dependencies, detailed tasks, expected files or modules, exit criteria, and any handoff notes needed by the next group.
7. Include concrete technical detail covering repository layout, module boundaries, runtime contracts, state/data models, persistence expectations, testing requirements, observability, failure handling, and acceptance criteria when the planning doc supports them.
8. Update any impacted planning indexes when adding or renaming workflow planning documents.
9. Summarize what was created or updated and call out any remaining assumptions or unresolved decisions.

Output expectations:

- the implementation doc must be execution-oriented, not just a summary
- the implementation doc must be detailed enough that an implementation team can use it as its primary build document
- prefer the smallest set of document edits that fully satisfies the request
