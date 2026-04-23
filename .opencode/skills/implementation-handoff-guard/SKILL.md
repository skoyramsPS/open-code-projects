# Skill: implementation-handoff-guard

Create and maintain a handoff document beside an implementation guide so work can resume cleanly in the next session.

## Purpose

Use this skill whenever implementation work starts, finishes, or becomes blocked.

The handoff document is the execution-status ledger for a specific implementation guide. It should eliminate guesswork about what is done, what remains, and where the next implementation session should resume.

## Default path

Unless the caller supplies a different path, use `implementation-handoff.md` in the same directory as the implementation guide.

## Required sections

1. Title and document links
2. Current status summary
3. TaskGroup progress table or checklist
4. Completed in this session
5. Verification evidence
6. Documentation updates
7. Open blockers or decisions needed
8. Next recommended slice
9. Session log

## Required data to record

- implementation guide path and status
- date of the latest update
- selected TaskGroup and task scope
- files changed in the session
- tests run, including command scope and result
- docs updated, including planning/business/developer/ADR changes when relevant
- unfinished work and resume instructions
- blockers, assumptions, or deviations from the implementation guide
- any pending approval-gated install, copy, or delete operation

## Update rules

- Create the handoff doc before or during the first implementation session if it does not exist.
- Update it at the end of every implementation session, including blocked sessions.
- If a task was partially completed, say exactly what is done and what remains.
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

## Quality bar

Someone who did not participate in the previous session should be able to open the handoff doc and answer:

- what is already done
- what evidence exists that it works
- what still needs to be built
- what should be done next
- what could block the next session

## Guidance sources consulted for this repo

- Project handoff checklist guidance emphasizes explicit status, outstanding risks, and transition-ready records instead of relying on tribal knowledge.
- GitHub task tracking guidance supports maintaining progress as discrete, reviewable items.

Reference URLs:

- `https://html.duckduckgo.com/html/?q=software+handoff+runbook+checklist`
- `https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/about-tasklists`
