# ADR Index

Use Architecture Decision Records for major workflow and subsystem changes.

## When an ADR is required

Create or update an ADR when a change:

- changes workflow topology, orchestration strategy, or persistence model
- changes contracts, schemas, or integration patterns in a lasting way
- introduces a long-lived tradeoff, constraint, or operational risk
- changes a repository-wide standard or default approach

## Naming

Use `ADR-0001-short-title.md`, `ADR-0002-short-title.md`, and so on.

## Template

- [ADR template](ADR-000-template.md)

## Records

- [ADR-0001: Add an implementation execution agent with a planning-folder handoff ledger](ADR-0001-implementation-execution-agent.md)
- [ADR-0002: Reorganize the repository into a multi-workflow `pipelines` package with a shared logging standard](ADR-0002-repo-reorganization.md)
