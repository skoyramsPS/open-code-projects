---
description: execute the next commit-sized slice from an implementation guide and update the handoff
agent: implementation-agent
---

Execute the next implementation slice from: `$1`

If `$2` is provided, use it as the handoff document. Otherwise, use `implementation-handoff.md` in the same directory as `$1`.

Required actions:

1. Inspect the implementation guide, current handoff doc, and relevant repository state.
2. If the handoff or guide says implementation has not started and is waiting for approval, begin only when the current user approval is explicit for `/implement-next`. Generic continuation wording such as `continue`, `go ahead`, `keep going`, `continue with your task`, or `summarize and continue` is not sufficient.
3. Use the `implementation-slice-guard` skill to choose the next eligible commit-sized slice.
4. Treat read-only repository inspection and safe git read/get commands as pre-approved.
5. Complete the whole next TaskGroup only if the remaining work is small and cohesive enough for one commit. Otherwise complete one task or one inseparable task cluster from that TaskGroup.
6. Use `pytest-tdd-guard` for Python behavior changes or risky refactors. Test execution is pre-approved.
7. Use `docs-update-guard` when the slice changes behavior, contracts, workflow docs, or developer/operator expectations.
8. Creating, editing, modifying, and moving files or folders within the selected slice are pre-approved when they directly follow the implementation guide.
9. Ask before installing packages or modules, before any delete operation, and before any copy operation.
10. Run relevant tests, fix issues within the selected slice, and keep the change set clean.
11. Update the handoff doc with status, changed files, verification evidence, blockers, the next recommended slice, and an explicit permission checkpoint for any additional implementation beyond the current slice.
12. Summarize what was completed and what remains.
13. Stop after the selected slice and ask the user whether to proceed with another `/implement-next` run if more work remains.
14. Treat the permission checkpoint as mandatory. Return after one slice and do not auto-chain another `/implement-next` run unless the user sends a fresh approval message after seeing that checkpoint.
