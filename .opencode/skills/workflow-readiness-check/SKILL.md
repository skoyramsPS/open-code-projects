---
name: workflow-readiness-check
description: review whether a significant workflow change is actually ready. use when someone asks if a workflow change is done, ready, complete, shippable, mergeable, or safe to hand off. check modularity, contracts, observability, testing, docs, and adr completeness.
---

# Workflow Readiness Check

Use this skill before claiming a significant workflow change is ready.

## Review checklist

### Architecture and modularity

- graph orchestration is separated from business logic and adapters
- reusable helpers are extracted from graph-specific code
- node responsibilities are clear and small

### Contracts and state

- state inputs and outputs are explicit
- schemas and interfaces are documented
- idempotency, retries, interrupts, and persistence are intentional

### Quality and operations

- failure handling is localized and actionable
- observability is good enough to debug workflow behavior
- major tradeoffs are captured in docs or ADRs

### Tests

- pytest evidence exists for changed behavior
- regression tests exist for bug fixes
- integration coverage exists for risky graph behavior when appropriate

### Documentation

- the documentation triad is updated when required
- `index.md` files are current
- ADRs are updated when architecture changed

## Required output

Return one of:

- `pass`
- `conditional pass`
- `block`

Then list the reasons, missing work, and the smallest next actions needed.
