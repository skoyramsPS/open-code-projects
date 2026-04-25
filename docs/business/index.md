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

- [Image Prompt Generation Workflow](Image-prompt-gen-workflow/index.md): current plain-language status, setup expectations, and operational guardrails for the image-generation workflow.
- [Template Upload Workflow](template-upload-workflow/index.md): plain-language import behavior, operator commands, resumability, and troubleshooting for JSON template uploads.
- [Implementation Execution Agent](implementation-execution-agent/index.md): what to expect from the agent that advances implementation guides in small, resumable slices.

## Cross-cutting initiatives

- [Repository Reorganization](repo-reorganization/index.md): rollout status, operator impact, and logging-foundation progress for the move into `workflows/pipelines/`.
