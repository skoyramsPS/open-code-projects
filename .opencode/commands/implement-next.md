---
description: execute the next commit-sized slice from an implementation guide and update the handoff
agent: implementation-agent
---

Execute the next implementation slice from: `$1`

If `$2` is provided, use it as the handoff document. Otherwise, use `implementation-handoff.md` in the same directory as `$1`.

Required actions:

1. Inspect the implementation guide, current handoff doc, and relevant repository state.
2. Use the `implementation-slice-guard` skill to choose the next eligible commit-sized slice.
3. Complete the whole next TaskGroup only if the remaining work is small and cohesive enough for one commit. Otherwise complete one task or one inseparable task cluster from that TaskGroup.
4. Use `pytest-tdd-guard` for Python behavior changes or risky refactors.
5. Use `docs-update-guard` when the slice changes behavior, contracts, workflow docs, or developer/operator expectations.
6. Run relevant tests, fix issues within the selected slice, and keep the change set clean.
7. Update the handoff doc with status, changed files, verification evidence, blockers, and the next recommended slice.
8. Summarize what was completed and what remains.
