# Business Documentation

Business docs explain workflows in plain language for non-technical readers.

## Include here

- workflow overviews
- when to use a workflow
- expected inputs and outputs
- examples for stakeholders or operators
- known limitations, risks, and guardrails
- troubleshooting written for non-developers

## Conventions

- write for readers who do not know the codebase
- prefer concrete examples and outcome-oriented language
- update this index when new business-facing docs are added or renamed

## Workflows

- [Image Prompt Generation Workflow](image-prompt-gen-workflow/index.md): current plain-language status, setup expectations, and operational guardrails for the image-generation workflow.
- [Template Upload Workflow](template-upload-workflow/index.md): plain-language import behavior, operator commands, resumability, and troubleshooting for JSON template uploads.
- [Implementation Execution Agent](implementation-execution-agent/index.md): what to expect from the clarification-first guide-writing step and the standard/autonomous agents that advance approved implementation guides in resumable slices.

## Cross-cutting initiatives

- [Repository Reorganization](repo-reorganization/index.md): completed rollout record, operator impact summary, and final migration state for the move into `workflows/pipelines/`.
