# Documentation Standards

## The documentation triad

For significant workflow or subsystem changes, update all three documentation views:

1. `docs/planning/` for goals, design, tradeoffs, implementation details, and acceptance criteria
2. `docs/business/` for non-technical readers who need plain-language workflow guidance
3. `docs/developer/` for maintainers who need setup, structure, contracts, and debugging guidance

## Significant change definition

Treat a change as significant when it adds, removes, or materially changes:

- workflows, nodes, edges, interrupts, or persistence boundaries
- schemas, contracts, public interfaces, or configuration
- user-visible behavior, operational behavior, or failure handling
- developer setup, testing strategy, or runtime assumptions
- architecture decisions that deserve an ADR

## Required index maintenance

Update `index.md` files whenever docs are added, removed, renamed, or materially changed.

Required index levels:

- `docs/index.md`
- top-level section indexes
- deeper indexes such as `docs/planning/adr/index.md`

## ADR rule

Create or update an ADR for major architectural decisions and long-lived tradeoffs. Store ADRs in `docs/planning/adr/`.

## Self-sufficiency rule

Documentation must be understandable without tribal knowledge. Include:

- purpose and scope
- assumptions and constraints
- examples and non-goals where relevant
- failure modes, limitations, or guardrails
- maintenance notes for long-lived systems

## Completion gate

Significant work is not complete until the relevant docs and indexes are updated.
