# LangGraph Workflow Standards

## Use LangGraph deliberately

Use LangGraph when the problem benefits from stateful orchestration, durable execution, interrupts, human review, resumability, or non-trivial routing. Use simpler Python functions or services when a full graph would add ceremony without value.

## Architecture rules

- keep graph orchestration separate from business logic and infrastructure adapters
- keep nodes small and single-purpose
- prefer reusable modules that can be imported outside the graph
- make side effects explicit and injectable
- prefer deterministic edges unless dynamic routing materially improves behavior

## Node contract pattern

Each node should be understandable in isolation.

Document for every node:

- required inputs from state
- outputs written back to state
- side effects and dependencies
- retry and idempotency expectations
- failure handling and escalation behavior

Recommended shape:

```python
def node_name(state, deps):
    """Return a state delta. Keep external effects behind deps."""
```

## State standards

- use typed state models
- keep state minimal but sufficient for execution, debugging, and auditability
- make transitions explicit and reviewable
- document stable schemas and migration considerations
- prefer durable identifiers for resumable work

## Durability, interrupts, and persistence

- choose checkpointing and persistence intentionally
- use idempotency keys or existing-result checks for expensive or external work
- add interrupt points for high-risk, destructive, or ambiguous actions
- document what can be resumed and from where

## Observability

- log graph-level and node-level events with enough metadata to debug behavior
- preserve rationale for important routing or tool-use decisions
- surface actionable failure reasons instead of generic errors

## Reuse standard

When a node, adapter, or helper could support another workflow, extract it into a shared module instead of burying it inside a graph-specific file.
