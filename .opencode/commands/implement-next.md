---
description: execute the next commit-sized slice from an implementation guide and update the handoff
agent: implementation-agent
---

Execute the next implementation slice from: `$1`

If `$2` is provided, use it as the handoff document. Otherwise, use `implementation-handoff.md` in the same directory as `$1`.

Required actions:

1. Inspect the implementation guide, current handoff doc, and relevant repository state.
2. Use the `implementation-slice-guard` skill to choose the next eligible commit-sized slice.
3. Treat read-only repository inspection and safe git read/get commands as pre-approved.
4. Complete the whole next TaskGroup only if the remaining work is small and cohesive enough for one commit. Otherwise complete one task or one inseparable task cluster from that TaskGroup.
5. Use `pytest-tdd-guard` for Python behavior changes or risky refactors. Test execution is pre-approved.
6. Use `docs-update-guard` when the slice changes behavior, contracts, workflow docs, or developer/operator expectations.
7. Creating, editing, modifying, and moving files or folders within the selected slice are pre-approved when they directly follow the implementation guide.
8. Ask before installing packages or modules, before any delete operation, and before any copy operation.
9. Run relevant tests, fix issues within the selected slice, and keep the change set clean.
10. Update the handoff doc with status, changed files, verification evidence, blockers, the next recommended slice, and an explicit permission checkpoint for any additional implementation beyond the current slice.
11. Summarize what was completed and what remains.
12. Stop after the selected slice and ask the user whether to proceed with another `/implement-next` run if more work remains.
