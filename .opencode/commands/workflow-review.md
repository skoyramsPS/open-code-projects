---
description: review a workflow change for modularity, readiness, docs, and tests
agent: langgraph-architect
---

Use the `workflow-readiness-check` skill and review: $ARGUMENTS

Required checks:

- reusable module boundaries
- typed state and explicit contracts
- retry, idempotency, persistence, and interrupt strategy
- observability and failure handling
- pytest coverage and regression risk
- documentation triad and ADR completeness

Return a clear pass, conditional pass, or block decision with reasons.
