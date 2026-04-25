---
description: review an implementation guide produced by /implementation-doc and tighten it against the source plan and current repo state
agent: implementation-doc-reviewer
---

Review the implementation guide at: `$1`

If `$2` is provided, treat it as the source planning document path. Otherwise default to `plan.md` in the same directory as `$1`.

If `$3` is provided, treat it as the sibling handoff path. Otherwise default to `implementation-handoff.md` in the same directory as `$1`.

This command runs as a follow-up to `/implementation-doc`. Its purpose is to make the implementation guide as detailed, scope-clear, technically explicit, and structurally complete as possible, and to close every gap between the source plan and the implementation guide. Where reasonable inference can close a gap, the command applies the fix and annotates it; where the fix would change scope, sequencing, ownership, contracts, tests, observability, acceptance criteria, or rollout behavior, the command stops and asks the user.

## Required actions

1. **Locate inputs.** Resolve the implementation guide, source plan, sibling handoff, and the planning index. If the directory contains multiple `implementation*.md` files (e.g. `implementation.md` plus an auto-versioned `implementation-vN.md`), use the version the planning index marks as current. If the index is unclear or missing, ask the user before continuing.
2. **Inspect repository state.** Read every file the plan and the guide reference, including the relevant `docs/standards/` files and any AGENTS.md / `.opencode/agents/*.md` content the plan or guide touches. Walk every directory the plan affects; capture what already exists in the target tree and what is still authoritative under the legacy tree. Read-only source-code inspection is pre-approved. Safe git read/get commands are pre-approved.
3. **Apply the `implementation-doc-review-guard` skill.** Walk every review category exhaustively: plan-to-implementation coverage, scope clarity, technical depth, structural completeness, verified-baseline accuracy, ambiguity sweep. Produce a findings list keyed by category, severity, and location.
4. **Cross-check against the source plan.** Confirm every plan-level decision, mapping table, phase, outcome, risk, and open question is reflected in the guide. The guide's appendices must reproduce every plan-level mapping table without glob shorthand. Anything the plan covers but the guide drops is a `gap` finding.
5. **Cross-check against repository reality.** Confirm the guide's `Verified repository baseline` section matches what the directories actually contain today. Anywhere the guide assumes baseline conditions that contradict reality is an `inconsistency` finding.
6. **Categorize findings into actions.** For each finding choose one of: apply directly (mechanical fixes only); apply with annotation (well-supported inferences, captured in a "Reviewer notes" subsection at the end of the affected section); ask the user (anything that could change scope, sequencing, ownership, contracts, tests, observability, acceptance criteria, or rollout behavior).
7. **Apply direct fixes to the implementation guide.** Use canonical task-ID format `TG{N}-T{M}` everywhere. Keep file enumerations explicit and complete (no globs, no `etc.`, no `…`). Keep exit criteria runnable; for purely doc-driven plans where shell verification does not apply, replace with a `Manual review checklist` whose items are objectively answerable yes/no. Add or expand appendices as required: file-by-file migration table; reference skeletons for new shared modules; contract references with worked examples; wrapper templates (Pattern 1 symbol re-export and Pattern 2 module alias) when compatibility scaffolding exists; configuration templates (`pyproject.toml`, etc.) when project metadata changes; checklist appendices for cross-cutting sweeps.
8. **Apply annotated fixes.** Each annotated change carries a "Reviewer notes" subsection naming the source-plan section that drives the inference and why the inference is well-supported.
9. **Update the sibling handoff** through `implementation-handoff-guard` when the review changes any structural fact the handoff records — TaskGroup table, task IDs, scope statements, completion evidence wording, blocker list, or the active-implementation-guide pointer. Do not change completion status; status changes belong to the implementation agent, not the reviewer.
10. **Compose clarification questions** if any finding requires user input. Write concise, numbered questions, each tagged with the finding(s) it would resolve. Send them to the user and stop. Resume only after answers are received; multiple back-and-forth rounds are acceptable.
11. **Compose the review report.** Return a structured report containing: verdict (`ready`, `ready with edits`, `needs clarification`, or `block`); findings table (category, severity, location, description, action); edits applied (explicit list with section references); edits proposed but not applied (with rationale); clarification questions (numbered); plan-coverage summary table mapping each plan-level concept to where it lives in the guide.
12. **Stop after the review and any applied edits.** Do not edit runtime code, tests, or non-planning documentation as part of `/implementation-doc-review`. Do not transition planning to implementation. The planning-to-implementation hard stop established by `/implementation-doc` still applies.
13. **End the response with the exact line** `USER_APPROVAL_REQUIRED: implementation may start only after explicit /implement-next approval`.

## Boundaries

- this command does not regenerate the implementation guide from scratch; that is `/implementation-doc`'s job
- this command does not delete or auto-version implementation guides; the user invokes `/implementation-doc` again if a fresh rewrite is wanted
- this command does not run pytest, build, or any code-changing tool
- this command does not edit application code, tests, or non-planning documentation
- this command must not silently change scope, sequencing, or contracts; ask the user instead

## Quality bar checklist

Before returning the review report, walk this checklist. Failing any item means the review is not done.

- [ ] every review category was applied; none were skipped
- [ ] every `gap` finding names the plan section that drives the fix
- [ ] every `inconsistency` finding cites the verified repository state that contradicts the guide
- [ ] every `vagueness` finding names the vague verb or shorthand and the explicit replacement
- [ ] every clarification question is asked directly, not paraphrased around
- [ ] no finding of severity `gap`, `ambiguity`, or `inconsistency` is left unresolved when the verdict is `ready` or `ready with edits`
- [ ] the report names the implementation guide path, the source plan path, and the sibling handoff path explicitly
- [ ] the canonical `TG{N}-T{M}` task-ID format is used consistently in any edits applied
- [ ] required appendices for the plan's domain are present after edits; appendices not justified by the plan are not padded in
- [ ] the `Verified repository baseline` section reflects what the agent actually inspected
- [ ] the `Permission gate` section ends with the exact required line

## Permission notes

- reading repository files (including source code) is pre-approved
- safe git read/get inspection commands are pre-approved
- writing/editing markdown files under `docs/planning/` is pre-approved
- do not edit runtime code, tests, or non-planning documentation as part of `/implementation-doc-review`

## Output expectations

- the review report must be actionable, not narrative; favor explicit findings over prose
- direct edits applied to the guide must be the smallest set that closes the finding
- annotated edits must carry their rationale inline so the user can verify
- clarification questions must be concise, numbered, and tagged with the finding(s) they resolve
- the response must make the planning-to-implementation hard stop unambiguous to the caller and to any later subagent invocation
