---
name: docs-update-guard
description: enforce documentation updates for significant workflow or subsystem changes. use when implementing, reviewing, merging, or marking complete any change that affects architecture, state, contracts, behavior, persistence, runtime assumptions, user-facing behavior, indexes, or adr-worthy decisions.
---

# Docs Update Guard

Use this skill as the documentation completion gate for significant changes.

## Step 1: Decide whether the gate applies

Treat the change as significant if it does any of the following:

- adds, removes, or materially changes workflows, nodes, edges, interrupts, persistence, or integrations
- changes state schemas, interfaces, configuration, behavior, retries, idempotency, or observability
- changes user-facing behavior, operational behavior, or developer setup
- introduces a long-lived tradeoff or architecture decision

If the change is not significant, say so explicitly and explain why the full gate is not required.

## Step 2: Update the documentation triad

For significant changes, update all relevant views:

1. `docs/planning/`
2. `docs/business/`
3. `docs/developer/`

Keep workflow slugs aligned across the three trees when workflow-specific folders exist.

## Step 3: Update indexes

Update every impacted `index.md`, including:

- `docs/index.md`
- relevant top-level section indexes
- deeper indexes such as `docs/planning/adr/index.md`

## Step 4: Check ADR requirements

Create or update an ADR under `docs/planning/adr/` when the change affects architecture, persistence strategy, state contracts, long-lived tradeoffs, or repository-wide defaults.

## Step 5: Validate doc quality

Ensure the docs are self-sufficient:

- planning docs explain goals, scope, architecture, tradeoffs, testing, and acceptance criteria
- business docs explain purpose, usage, examples, limitations, and plain-language troubleshooting
- developer docs explain structure, setup, contracts, extension points, debugging, and maintenance notes

## Required output

Return:

- whether the gate was triggered
- which docs were updated
- which indexes were updated
- whether an ADR was added or updated
- any remaining documentation gaps blocking completion
