# Developer Documentation

Developer docs make workflows maintainable without relying on tribal knowledge.

## Include here

- project structure and module responsibilities
- setup and environment requirements
- state contracts and schemas
- testing approach and commands
- runtime, deployment, and operational notes
- extension points and debugging guidance

## Conventions

- document the why behind non-obvious patterns
- show code paths, contracts, and failure modes explicitly
- update this index when new developer docs are added or renamed

## Workflows

- [Image Prompt Generation Workflow](Image-prompt-gen-workflow/index.md): module boundaries, config contracts, and current test commands for the image-generation workflow.
- [Template Upload Workflow](template-upload-workflow/index.md): graph shape, persistence contracts, CLI/library surface, and closeout verification guidance for template imports.
- [Implementation Execution Agent](implementation-execution-agent/index.md): invocation, skill reuse, and handoff contracts for both the one-slice and autonomous multi-slice implementation agents.

## Cross-cutting initiatives

- [Repository Reorganization](repo-reorganization/index.md): migration status, shared logging foundation details, and verification guidance for the phased package move.
