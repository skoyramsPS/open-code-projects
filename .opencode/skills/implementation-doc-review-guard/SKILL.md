---
name: implementation-doc-review-guard
description: review an implementation guide for scope clarity, technical depth, structural completeness, and plan-to-implementation coverage. use when an implementation guide has been created or updated and a thorough review is required before handoff. cross-checks the guide against its source plan, flags gaps, ambiguities, and vague tasks, and produces an actionable issues list.
---

# Implementation Doc Review Guard

Use this skill when an implementation guide must be reviewed against its source plan and the current repository state. The skill enforces the same quality bar that `.opencode/commands/implementation-doc.md` requires of newly authored guides, plus a coverage check that nothing in the plan is dropped, ignored, or quietly reinterpreted.

The skill produces a structured review with a verdict, a categorized issues list, suggested edits, and a list of clarification questions that must be sent back to the user before any update can finalize.

## Inputs

- path to the implementation guide under review (required)
- path to the source plan (defaults to `plan.md` in the same directory)
- path to the sibling handoff (defaults to `implementation-handoff.md` in the same directory)
- the current repository state (read-only inspection)

If the implementation guide directory contains multiple `implementation*.md` files (e.g. an `implementation.md` plus an auto-versioned `implementation-v2.md`), the latest authoritative one named in the planning index is the target. If the index is unclear, ask the user before proceeding.

## Review categories

The review is organized into the categories below. Each category produces zero or more findings. A finding is one of: `pass`, `gap`, `ambiguity`, `vagueness`, `inconsistency`, or `structural`.

### Category 1 — Plan-to-implementation coverage

Goal: confirm the guide covers every concept, decision, mapping, and acceptance criterion in the plan, and flags anywhere the guide adds, removes, reorders, or reinterprets plan content without an explicit Locked Decision.

Checks:

- every "decision locked from clarification" in the plan is reflected in the guide's `Locked decisions and resolved ambiguities` section
- every plan-level mapping table (file moves, slug renames, env-var rosters, schema diffs) is reproduced in the guide's appendices with no glob shorthand
- every plan-level execution phase (or equivalent unit) maps onto exactly one TaskGroup, or is explicitly split with a recorded rationale
- every plan-level outcome listed under "Why" / "Outcomes" is covered by at least one TaskGroup's exit criteria
- every plan-level risk has a corresponding mitigation visible in the guide (in a TaskGroup's tasks, exit criteria, rollback notes, or a cross-cutting section)
- every plan-level open question is either resolved as a Locked Decision or carried forward into the guide's `Open issues and known limitations`
- the guide does not silently introduce scope that is absent from the plan; if it does, the addition is recorded as a Locked Decision with rationale

### Category 2 — Scope clarity (per TaskGroup and per task)

Goal: confirm every task has a clearly bounded scope and every TaskGroup has explicit in/out-of-scope lists.

Checks:

- every TaskGroup has both `In scope` and `Out of scope` sections
- the `Out of scope` list explicitly names nearby work that the TaskGroup must not absorb
- every task carries a single-sentence scope statement
- no task uses vague verbs without enumeration: "update imports", "fix references", "rewire as needed", "adjust callers" must be replaced with explicit targets
- no task says "etc." or "..." or relies on globs in its file list
- no task implicitly depends on side work that lives in another TaskGroup without naming the dependency
- TaskGroup ownership of cross-cutting concerns (logging adoption, doc-slug normalization, asset moves) is unambiguous

### Category 3 — Technical depth

Goal: confirm the guide includes enough technical detail that the implementer never has to infer structure.

Checks:

- every non-obvious task includes a code snippet, skeleton, or command sequence
- new shared modules introduced by the plan have a reference skeleton in an appendix that exposes the full public surface
- new contracts (logging fields, schemas, state shapes, wire formats) are documented in an appendix with at least one worked example
- compatibility scaffolding (wrappers, shims, aliases) has a wrapper template in an appendix; if multiple patterns are needed, both patterns are spelled out
- configuration changes (`pyproject.toml`, `package.json`, `.env.example`) include a template or full diff
- every cross-cutting sweep (slug rename, env-var migration) has a checklist appendix listing the exact files to touch
- every TaskGroup's task list includes a focused verification step (a shell command, grep, or pytest invocation) at the end of each task

### Category 4 — Structural completeness

Goal: confirm the guide follows the canonical structure required by `.opencode/commands/implementation-doc.md`.

Checks:

- the guide opens with a metadata table (status, version, date, source plan, sibling handoff, ADR if applicable, audience, authority, execution mode)
- a `Verified repository baseline` section exists and reflects actual repo state, not the plan's assumptions
- a `Locked decisions and resolved ambiguities` section is numbered and explicit
- a `Target architecture` section covers final layout, ownership rules, and runtime/state/persistence/observability/failure contracts
- a `Cross-cutting requirements` section covers testing, documentation, observability, code-quality, rollback policy
- a `TaskGroup overview` table summarizes every TaskGroup with dependency and primary outcome
- every TaskGroup includes all twelve required sections in the prescribed order: Goal, Dependencies, Pre-flight checklist, In scope, Out of scope, Detailed task list, Expected files (full enumeration), Test plan, Documentation impact, Exit criteria (verifiable), Rollback notes, Handoff to the next TaskGroup
- every task ID follows the canonical `TG{N}-T{M}` format and the IDs are referenced consistently in cross-references
- a `Cross-TaskGroup verification matrix` exists and is consistent with the per-TaskGroup exit criteria
- a `Program-level acceptance criteria` section exists and aligns with the TaskGroup exit criteria
- `Out of scope (program-wide)` and `Open issues and known limitations` exist
- a `Glossary` section exists when the doc uses domain-specific shorthand
- a `Permission gate` section exists and ends with the exact line `USER_APPROVAL_REQUIRED: implementation may start only after explicit /implement-next approval`
- mandatory appendices are present (file-by-file migration table for migration plans; reference skeletons for new shared modules; contract references; wrapper templates; configuration templates; checklist appendices for cross-cutting sweeps); appendices that have no plan justification are omitted rather than padded

### Category 5 — Verified-baseline accuracy

Goal: confirm the `Verified repository baseline` section reflects current repo reality and that the rest of the guide is consistent with it.

Checks:

- every directory the plan touches is described in the baseline section
- target-tree assets that already exist are listed accurately
- legacy assets that are still authoritative are listed accurately
- import paths, test runner commands, and configuration references in the baseline match what the repo actually uses today
- TaskGroups do not assume baseline conditions that contradict reality (e.g. assuming a file does not exist when it does, or assuming a wrapper layer when none is in place)
- where reality and the plan disagree, the disagreement is resolved by an explicit Locked Decision in the guide, not silently absorbed

### Category 6 — Ambiguity sweep

Goal: surface every place where two reasonable readings of the guide would produce different implementation paths.

Checks:

- no place in the guide says "or equivalent" / "as appropriate" / "if needed" without spelling out the decision rule
- no test plan says "add tests where coverage is missing" without naming the missing scenarios
- no exit criterion is qualitative when a quantitative or runnable check is possible
- no rollback note is boilerplate; every one is specific to the TaskGroup
- no Locked Decision is partial — each fully resolves the ambiguity it claims to resolve
- every reference to a temporary scaffolding item also names the TaskGroup that removes it

## Action policy

Findings drive one of three actions:

1. **Update the implementation guide directly** — when the fix is mechanical (vague verb → enumerated list, missing exit criterion → runnable command, missing snippet → code skeleton, missing appendix entry → table row). The reviewer agent has edit permission for `docs/planning/` markdown.
2. **Update the implementation guide with an annotated assumption** — when the fix requires inferring intent from the plan and the inference is well-supported. Annotate the change in a "Reviewer notes" subsection so the user can verify it.
3. **Ask the user a clarification question** — when the fix would change scope, sequencing, ownership, contracts, tests, observability, acceptance criteria, or rollout behavior. Send concise question(s) and stop. Resume only after answers are received.

Never silently change scope, sequencing, or contracts. Never rewrite a Locked Decision based on inference; if a Locked Decision looks wrong, ask.

## Output

Return a review report containing:

1. **Verdict** — one of: `ready` (no findings beyond passes), `ready with edits` (mechanical findings were applied; user should review the diff), `needs clarification` (the user must answer questions before the guide can be finalized), `block` (structural problems require a rewrite).
2. **Findings table** — one row per finding with category, severity, location (section / TaskGroup / task ID / appendix), description, recommended action.
3. **Edits applied** — explicit list of every change the reviewer made to the guide and to the handoff, with the relevant section references.
4. **Edits proposed but not applied** — fixes the reviewer would make but that require user confirmation first; include a one-line rationale per item.
5. **Clarification questions for the user** — concise, numbered, each tagged with the finding(s) it would resolve.
6. **Plan-coverage summary** — a short table mapping each plan-level concept (decisions, mappings, phases, outcomes, risks, open questions) to where it lives in the guide; flag anything missing.

## Quality bar

The review is not done if any of the following is true:

- any finding category was skipped
- a `gap` finding was applied without naming the plan section that drives the fix
- a clarification question paraphrases a plan ambiguity instead of asking about it directly
- the verdict is `ready` while findings of severity `gap`, `ambiguity`, or `inconsistency` are unresolved
- the report does not name the implementation guide path or the source plan path explicitly

## Reuse rule

This skill is the canonical review rubric for implementation guides in this repository. New checks land here first before they appear in command or agent prompts.
