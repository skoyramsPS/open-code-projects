# Documentation Index

This repository keeps all durable project documentation under `docs/`.

## Sections

- [Planning](planning/index.md): goals, design, implementation plans, ADRs, risks, and rollout material.
- [Business](business/index.md): non-technical documentation for stakeholders, operators, and end users.
- [Developer](developer/index.md): maintainer documentation, setup, architecture, debugging, and extension guidance.
- [Standards](standards/index.md): repo-wide rules that OpenCode loads through `opencode.json`.

## Workflow quick links

- Template Upload Workflow (slug: `template-upload-workflow`)
  - [Planning](planning/template-upload-workflow/index.md)
  - [Business](business/template-upload-workflow/index.md)
  - [Developer](developer/template-upload-workflow/index.md)
- Image Prompt Generation Workflow (target slug: `image-prompt-gen-workflow`; folders rename to lowercase in Phase 2 of the reorganization)
  - [Planning](planning/Image-prompt-gen-workflow/index.md)
  - [Business](business/Image-prompt-gen-workflow/index.md)
  - [Developer](developer/Image-prompt-gen-workflow/index.md)

## Cross-cutting initiatives

- [Repository Reorganization](planning/repo-reorganization/index.md): plan and ADR for the multi-workflow `pipelines` package and the shared logging standard.

## Cross-cutting rules

- Every level maintains an `index.md`.
- Significant changes must update the documentation triad.
- Major architectural decisions must be recorded in `docs/planning/adr/`.
- Workflow-specific docs should use the same slug in all three doc trees, lowercase-hyphenated, ending in `-workflow`.
- The Python-module-to-doc-slug mapping is recorded in [`docs/standards/repo-structure.md`](standards/repo-structure.md).
