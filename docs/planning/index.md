# Planning Documentation

Planning docs explain what is being built, why, and how implementation should proceed.

## Include here

- design and requirements docs
- implementation plans
- architecture notes
- rollout and acceptance criteria
- risk registers and deferred decisions
- ADRs in `adr/`

## Conventions

- keep one folder per workflow or subsystem when material grows beyond a single page
- use the same workflow slug across `docs/business/` and `docs/developer/`
- update this index when new planning docs are added or renamed

## ADRs

- [ADR index](adr/index.md)

## Workflows

- [Image Prompt Generation Workflow](Image-prompt-gen-workflow/index.md): plan and implementation guide for the LangGraph-based prompt-routing and serial image-generation workflow.
- [Template Upload Workflow](template-upload-workflow/index.md): planning, implementation guide, and handoff for importing template JSON into the shared SQLite template library.
- [Implementation Execution Agent](implementation-execution-agent/index.md): design and operating rules for clarification-gated implementation guides plus resumable commit-sized implementation slices in both standard and autonomous modes.

## Cross-cutting initiatives

- [Repository Reorganization](repo-reorganization/index.md): plan, implementation guide, handoff, and ADR for moving to the multi-workflow `pipelines` package and adopting a shared logging standard.
