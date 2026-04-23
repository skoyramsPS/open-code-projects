---
name: pytest-tdd-guard
description: enforce pytest-first and tdd-oriented testing for python behavior changes. use when adding features, fixing bugs, changing workflow behavior, refactoring risky code, or before marking python changes complete.
---

# Pytest TDD Guard

Use this skill whenever Python behavior changes or when a completion check needs testing evidence.

## Step 1: Identify the behavior change

Summarize what changed:

- feature or behavior addition
- bug fix
- refactor risk
- contract or schema change
- workflow routing, persistence, or interrupt change

## Step 2: Apply the TDD loop when practical

Preferred loop:

1. write the smallest failing test
2. make the smallest implementation change that passes
3. refactor with tests green

If the work cannot follow strict TDD, add or update the relevant tests before marking the task complete and explain why the loop was adapted.

## Step 3: Choose the right test layers

Use the smallest sufficient scope first:

- unit tests for reusable helpers and node logic
- integration tests for graph assembly, persistence, adapters, and routing
- regression tests for fixed bugs
- end-to-end tests only for critical workflows

## Step 4: Use pytest conventions

- default command: `pytest -q`
- prefer targeted test paths or node ids first
- mock LLM, network, filesystem, and tool boundaries in unit tests
- keep tests deterministic and readable
- when this skill is used from the implementation workflow, pytest execution is pre-approved and should not be delayed behind an avoidable permission prompt

## Step 5: Block or pass completion

A change is not ready if behavior changed and testing evidence is missing.

## Required output

Return:

- the behavior under test
- tests added or updated
- pytest scope run or still required
- failures, gaps, or flaky-risk areas
- whether the change should be blocked on missing tests
