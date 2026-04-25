---
description: create a standalone, execution-ready technical implementation guide from a planning doc
agent: docs-writer
---

Create or update a standalone technical implementation guide from the planning document at: `$1`

## Output path resolution

1. If `$2` is provided, use it as the implementation guide's output path.
2. Otherwise, the default path is `implementation.md` in the same directory as `$1`.
3. **Never overwrite an existing non-empty implementation guide.** Before writing, check whether the resolved output path already exists and is non-empty. If it does:
   - resolve the next free path `implementation-v2.md`, `implementation-v3.md`, … (the next integer that yields a non-existent file) in the same directory;
   - write to that auto-incremented path instead;
   - record in the final summary that the previous implementation guide was preserved at its original path and the new guide was written to the auto-incremented path.
4. Always create or update the sibling `implementation-handoff.md` next to the implementation guide. Seed it from the current repository state and end it with an explicit permission checkpoint that asks the user to approve `/implement-next` before any implementation begins.

## Required actions

1. **Inspect deeply before drafting.** Read the source planning document, every related planning, business, and developer doc for the same domain, the documentation standards under `docs/standards/`, the relevant `AGENTS.md` and `.opencode/agents/*.md` files, and the actual repository state for every directory the plan touches. Read-only source-code inspection is pre-approved. Safe git read/get commands are pre-approved.
2. **Build a verified repository baseline.** Walk the directories the plan affects, list the files that exist today, note which target-tree assets are already in place, note which legacy assets are still authoritative, and capture import/test/configuration reality. The implementation guide must include a `Verified repository baseline` section grounded in this inspection — not in what the plan assumes.
3. **Identify material ambiguities and conflicts.** Treat the following as blocking: any place where the plan disagrees with current repository state; any place where the plan leaves scope, sequencing, file ownership, contracts, tests, observability, acceptance criteria, rollout behavior, or cleanup responsibility underspecified; and any place where two reasonable interpretations of the plan would produce different implementation paths.
4. **Stop and ask if the plan and reality conflict.** If verified repository state contradicts the plan in a way that affects scope, sequencing, file lists, or contracts, stop and ask the user concise clarification question(s) before drafting. Resume only after answers are received, even if multiple clarification rounds are needed. Do **not** silently reconcile a conflict by guessing which side wins.
5. **Stop and ask for material ambiguities that are not plan-vs-reality conflicts.** Same rule: ask the user, do not guess.
6. **Produce a self-sufficient technical implementation document for the delivery team.** The implementation team must be able to execute the migration with this document alone, without reopening the plan except for historical context.
7. **Resolve every planning ambiguity or contradiction explicitly inside the implementation document** under a `Locked decisions and resolved ambiguities` (or equivalently named) section. Do not leave decisions implied.
8. **Convert the planned work into ordered TaskGroups.** TaskGroups are sequential. Each later TaskGroup depends on the prior ones' exit criteria. Within a TaskGroup, tasks are also numbered and dependency-ordered.
9. **Use the canonical task ID format `TG{N}-T{M}`.** TaskGroups are `TG1`, `TG2`, … Tasks within a TaskGroup are `TG{N}-T1`, `TG{N}-T2`, … Reference tasks by ID consistently across the document.
10. **Make every TaskGroup specific enough to execute without guesswork.** Split broad work until that bar is met. Do not paper over vagueness with extra prose.
11. **For every TaskGroup, include all of the following sections, in this order:**
    1. **Goal** — the single outcome this TaskGroup must produce.
    2. **Dependencies** — verifiable preconditions referencing prior TaskGroups by ID.
    3. **Pre-flight checklist** — concrete shell commands or grep patterns the implementer can run to confirm prereqs.
    4. **In scope** — exhaustive list of work this TaskGroup owns.
    5. **Out of scope** — explicit list of nearby work this TaskGroup must not absorb.
    6. **Detailed task list** — numbered `TG{N}-T{M}` tasks, each with: clear scope statement, explicit file paths to create/modify/move/delete, exact commands or `git mv` invocations where applicable, code snippets/skeletons for non-obvious parts, and a focused verification step at the end of the task.
    7. **Expected files (full enumeration)** — every file the TaskGroup creates, modifies, moves, or deletes. No glob shorthand. List paths explicitly.
    8. **Test plan** — required new or updated tests, focused-to-broad pytest invocation sequence, and any required smoke/CLI checks.
    9. **Documentation impact** — explicit list of docs to update (planning, business, developer triad plus impacted indexes, AGENTS.md, agent files, ADR if relevant).
    10. **Exit criteria (verifiable)** — green-bar conditions expressed as runnable shell commands, grep checks, or test invocations. If the plan is purely documentation-driven and shell verification is not applicable, replace with a `Manual review checklist` whose items are objectively answerable yes/no questions.
    11. **Rollback notes** — what to do if this TaskGroup must be reverted partway, and what state the repository returns to.
    12. **Handoff to the next TaskGroup** — facts the next TaskGroup needs, and any temporary scaffolding introduced here that a later TaskGroup must remove.
12. **Required top-level structure of the implementation guide:**
    1. Title plus metadata table (status, version, date, source plan, sibling handoff, ADR if applicable, audience, authority, execution mode).
    2. `How to use this document` — short reading guide.
    3. `Executive summary` — what, why, outcome.
    4. `Verified repository baseline` — the inspection result from step 2 above.
    5. `Locked decisions and resolved ambiguities` — numbered, each item explicit.
    6. `Target architecture` — final layout, ownership rules, runtime/state/persistence/observability/failure contracts.
    7. `Cross-cutting requirements` — testing, documentation, observability, code-quality, rollback policy.
    8. `TaskGroup overview` — table summarizing TG1..TGn with dependencies and primary outcomes.
    9. `Reading the TaskGroup sections` — short note explaining the section template (matches item 11 above).
    10. `TaskGroup details` — one section per TaskGroup using the template.
    11. `Cross-TaskGroup verification matrix` — table showing which checks must pass at which TaskGroup boundary.
    12. `Program-level acceptance criteria` — the final list that defines "migration complete".
    13. `Out of scope (program-wide)` — what this guide explicitly does not authorize.
    14. `Open issues and known limitations` — items to revisit.
    15. `Glossary` — short.
    16. `Permission gate` — a hard-stop section ending with the exact line `USER_APPROVAL_REQUIRED: implementation may start only after explicit /implement-next approval`.
    17. `Appendices` — required (see step 13).
13. **Appendices are mandatory.** At minimum include the appendices that the plan's domain calls for. For migrations, always include:
    - **Appendix A** — full file-by-file migration mapping (legacy path → target path; no glob shorthand). When the migration introduces compatibility scaffolding, include a third column for the wrapper/shim path.
    - **Appendix B** — reference skeletons for any new shared module the plan calls for (e.g. logging module, runtime helper). Include the full public surface as code so the implementer does not infer structure.
    - **Appendix C** — domain reference (e.g. logging field reference with example records, schema reference, contract reference) when the plan introduces a new contract.
    - **Appendix D** — wrapper/shim templates with full content when the plan introduces compatibility scaffolding. Include a Pattern 1 / Pattern 2 split if the plan calls for both symbol re-exports and module aliasing.
    - **Appendix E** — configuration templates (`pyproject.toml`, `package.json`, etc.) when the plan changes project metadata.
    - **Appendix F** — checklist-style appendices for cross-cutting sweeps (doc-slug renames, env-var migrations, etc.) when the plan calls for them.
    Appendices are not filler. Include any appendix the plan justifies; do not include appendices that have no content.
14. **Always include reference skeletons and full enumerated tables.** Snippets are required where the implementer would otherwise have to infer structure. Tables must list every entry explicitly — no `*.py` shorthand, no `etc.`, no `…`.
15. **Tighten ruthlessly.** Re-read each task before finalizing. If a task says "update imports across moved files" without listing the modules whose imports change, that task is too vague — split it or list the modules. If a task says "expected files: every node module" without enumerating them, expand the enumeration. Vague tasks are the failure mode this command exists to prevent.
16. **Update any impacted planning indexes** when adding or renaming workflow planning documents. When auto-versioning has produced an `implementation-vN.md`, link both the old and new files from the index with a note explaining which is current.
17. **Create or update the sibling `implementation-handoff.md`** with current status, TaskGroup table (using the canonical TG/T IDs), resolved clarifications, any still-blocking assumptions, exact next recommended slice, and the explicit note that implementation must not start until the user grants permission.
18. **Summarize what was created or updated** and call out remaining assumptions or unresolved decisions. If a previous implementation guide was preserved, name it.
19. **Stop after the implementation guide, index updates, and handoff updates are complete.** Do not edit application code, tests, runtime documentation, or examples as part of this command.
20. **End with a direct handoff** asking the user whether to proceed with `/implement-next <implementation-doc> [handoff-doc]`.
21. **End the handoff and the final summary with the exact line** `USER_APPROVAL_REQUIRED: implementation may start only after explicit /implement-next approval`.
22. **Generic continuation wording** such as `continue`, `go ahead`, `keep going`, `continue with your task`, or `summarize and continue` does **not** count as approval. Implementation may begin only after a later user message explicitly invokes `/implement-next <implementation-doc> [handoff-doc]` or clearly says `approve /implement-next ...`.

## Quality bar checklist

Before finalizing, the agent must mentally walk through this list. Failing any item means the guide is not ready.

- [ ] Every TaskGroup has all twelve required sections in the prescribed order.
- [ ] Every task carries a `TG{N}-T{M}` ID and a clear, single-sentence scope statement.
- [ ] Every task lists the explicit files it touches — no globs, no `etc.`, no `…`.
- [ ] Every TaskGroup's `Expected files` section enumerates every file end-to-end.
- [ ] Every TaskGroup's `Exit criteria` lists runnable shell commands or grep checks (or a manual review checklist when shell verification does not apply).
- [ ] Every TaskGroup has a `Rollback notes` section that is concrete, not boilerplate.
- [ ] Every non-obvious task carries a code snippet, skeleton, or command sequence.
- [ ] The `Verified repository baseline` section reflects what the agent actually inspected, not what the plan claims.
- [ ] Every plan-vs-reality conflict is resolved by an explicit Locked decision, not silently smoothed over.
- [ ] All required appendices are present and non-empty; tables enumerate every entry.
- [ ] No vague verb survives final review: "update imports", "fix references", "rewire as needed" must be replaced by enumerated targets.
- [ ] The TaskGroup overview table and the cross-TaskGroup verification matrix are both present and consistent with the TaskGroup sections.

## Permission notes

- reading repository files (including source code) is pre-approved
- safe git read/get inspection commands are pre-approved
- writing/editing markdown files under `docs/planning/` is pre-approved
- do not edit runtime code or tests as part of `/implementation-doc`

## Output expectations

- the implementation doc must be execution-oriented, not a summary
- the implementation doc must be detailed enough that an implementation team can use it as its primary build document
- the implementation doc must minimize assumptions by locking scope and technical expectations per TaskGroup
- if assumptions remain that could affect implementation behavior, the command must ask the user for clarification instead of guessing
- code-affecting TaskGroups must include representative pseudocode, code skeletons, or call-site snippets for non-obvious work
- length follows necessity, not a fixed ceiling — verbosity is acceptable when it removes ambiguity, but every long passage must be doing real work
- prefer the smallest set of document edits that fully satisfies the request
- this command is planning-only and handoff-only; it must not auto-transition into implementation work
- the output must make the hard stop unambiguous to the caller and to any later subagent invocation
