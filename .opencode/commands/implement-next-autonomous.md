---
description: execute implementation-guide slices autonomously until completion or an approval-gated action blocks progress
agent: autonomous-implementation-agent
---

Execute implementation-guide slices from: `$1`

If `$2` is provided, use it as the handoff document. Otherwise, use `implementation-handoff.md` in the same directory as `$1`.

Required actions:

1. Inspect the implementation guide, current handoff doc, and relevant repository state.
2. If the handoff or guide says implementation has not started and is waiting for approval, begin only when the current user approval is explicit for `/implement-next-autonomous`. Generic continuation wording such as `continue`, `go ahead`, `keep going`, `continue with your task`, or `summarize and continue` is not sufficient.
3. Use the `implementation-slice-guard` skill to choose the next eligible commit-sized slice, and repeat that selection before each later slice in the same run.
4. Treat read-only repository inspection and safe git read/get commands as pre-approved.
5. Complete the whole next TaskGroup only if the remaining work is small and cohesive enough for one commit. Otherwise complete one task or one inseparable task cluster from that TaskGroup.
6. Use `pytest-tdd-guard` for Python behavior changes or risky refactors. Test execution is pre-approved, including `uv run` pytest invocations.
7. Treat local version checks such as `python3 --version` and `uv --version` as pre-approved.
8. Use `docs-update-guard` when the slice changes behavior, contracts, workflow docs, or developer/operator expectations.
9. Creating, editing, modifying, and moving files or folders within the selected slice are pre-approved when they directly follow the implementation guide.
10. Always ask before installing packages or modules, before any delete operation, before any copy operation, and before `git push` or any git-related remote mutation.
11. Run relevant tests, fix issues within the selected slice, and keep the change set clean.
12. Update the handoff doc after every completed slice with status, changed files, verification evidence, blockers, the next recommended slice, and whether any further approval is required.
13. If more work remains and the next slice does not require an approval-gated action or clarification, auto-approve the next handoff checkpoint and continue within the same run.
14. Stop only when the guide is complete or when a gated action, blocker, or unresolved question requires user input.
15. Summarize what was completed in this session, what remains, why execution stopped, and any approval still required before work can continue.
