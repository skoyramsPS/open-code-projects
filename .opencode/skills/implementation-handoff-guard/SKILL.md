# Skill: implementation-handoff-guard

Create and maintain a handoff document beside an implementation guide so work can resume cleanly in the next session.

## Purpose

Use this skill whenever implementation work starts, finishes, or becomes blocked, **and** whenever a new or updated implementation guide is created (the `/implementation-doc` command always triggers this skill).

The handoff document is the execution-status ledger for a specific implementation guide. It eliminates guesswork about what is done, what remains, and where the next implementation session should resume.

## Default path

Unless the caller supplies a different path, use `implementation-handoff.md` in the same directory as the implementation guide.

## Pairing rule

The handoff document is paired one-to-one with a single implementation guide. When a new auto-versioned implementation guide is created (e.g. `implementation-v2.md` written next to a preserved `implementation.md`), the handoff document points at the new authoritative guide and explicitly names the preserved one as historical reference. There is exactly one active handoff per implementation domain at any time.

## Required sections

1. **Title and document links** — link the active implementation guide, any preserved prior implementation guides, the source plan, the planning index, business and developer triad indexes, and the relevant ADR.
2. **Current status summary** — concise status across all TaskGroups; what is true after the last session.
3. **TaskGroup progress table** — one row per TaskGroup, using the canonical `TG{N}` IDs, with status from the recommended state set below and a brief notes column.
4. **Last completed slice** — selected TaskGroup and slice; reference any task by `TG{N}-T{M}` ID; rationale for slice size; bullet list of completed work.
5. **Files changed in this session** — explicit enumeration; no globs.
6. **Tests run and results** — exact commands and outcomes.
7. **Documentation updated** — split by triad (planning, business, developer) plus README/setup docs and ADR.
8. **Blockers or open questions** — remaining issues, approval-gated steps, environment limitations, deviations from the implementation guide.
9. **Exact next recommended slice** — which TaskGroup, which task ID, which scope; why this slice was chosen; explicit boundaries for the next session.
10. **Session log** — newest at the bottom; one entry per session, dated, listing what changed and why.
11. **Permission checkpoint** — explicit approval-gating notes for the next slice and for any install/copy/delete/git-push/remote-mutation steps.

## Required data to record

- the active implementation guide path and status
- any preserved prior implementation guide(s) with a one-line note explaining why they were preserved
- date of the latest update
- selected TaskGroup and slice, referenced by `TG{N}-T{M}` IDs
- files changed in the session (explicit enumeration, no globs)
- tests run, including command, scope, and result
- docs updated, including planning/business/developer/ADR changes when relevant
- unfinished work and resume instructions
- blockers, assumptions, or deviations from the implementation guide
- any pending approval-gated install, copy, delete, or remote-mutation operation

## Update rules

- Create the handoff doc before or during the first implementation session if it does not exist.
- Update it at the end of every implementation session, including blocked sessions.
- Update it when a new implementation guide is created or auto-versioned, even if no implementation work has happened yet — the handoff must always point at the currently authoritative guide.
- If a task was partially completed, say exactly what is done and what remains. Reference the task by its `TG{N}-T{M}` ID.
- If repository reality differs from the handoff doc, correct the handoff doc instead of silently continuing.
- If implementation sequencing changes, record the reason and point back to the implementation guide or ADR.
- If progress is blocked on an approval-gated install, copy, or delete step, record that explicitly so the next session does not rediscover it.

## Recommended format

Use concise Markdown sections and checklists. Favor explicit status over prose.

Recommended TaskGroup states:

- `not started`
- `in progress`
- `completed`
- `blocked`

When a slice is referenced, name it as `TG{N}-T{M}` (or as a small range like `TG2-T3 → TG2-T6` when a slice covers multiple tasks).

## Quality bar

Someone who did not participate in the previous session should be able to open the handoff doc and answer:

- which implementation guide is currently authoritative
- what is already done, with task IDs
- what evidence exists that it works (commands, results)
- what still needs to be built
- what should be done next, with task IDs and explicit boundaries
- what could block the next session
- whether any approval-gated step is pending

## Permission gate

The handoff doc must end with an explicit permission checkpoint. State whether the next recommended slice is pre-approved under any standing autonomous flow, and explicitly call out any install, copy, delete, git-push, or remote-mutation work that still requires user approval. The implementation-guide rule that bars implementation from starting without explicit `/implement-next` approval applies until that command is invoked.

## Guidance sources consulted for this repo

- Project handoff checklist guidance emphasizes explicit status, outstanding risks, and transition-ready records instead of relying on tribal knowledge.
- GitHub task tracking guidance supports maintaining progress as discrete, reviewable items.

Reference URLs:

- `https://html.duckduckgo.com/html/?q=software+handoff+runbook+checklist`
- `https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/about-tasklists`
