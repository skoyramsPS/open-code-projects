# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG1 foundation
- Last updated: 2026-04-23

## What exists today

The repository now contains the reusable foundation for the image prompt generation workflow:

- environment-driven configuration loading with `.env` fallback
- validated state and schema contracts for router plans, prompts, image results, and run summaries
- a frozen dependency container that later workflow nodes will receive explicitly
- a local project layout for tests, examples, run artifacts, logs, and image outputs

This slice does **not** yet execute the full workflow. It establishes the contracts that later slices will use for database access, routing, caching, image generation, and reporting.

## Expected operator inputs

When later slices are added, operators will provide:

- a free-form user prompt
- Azure OpenAI connection settings
- optional workflow controls such as dry-run, panel count, budget, and resume identifiers

For now, the only supported operational setup is preparing the environment variables documented in `ComicBook/.env.example`.

## Expected outputs later in the workflow

The completed workflow is planned to produce:

- generated images under `image_output/<run_id>/`
- human-readable run reports under `runs/<run_id>/report.md`
- structured summaries under `logs/<run_id>.summary.json`

Those runtime artifacts are not produced yet in this foundation slice.

## Guardrails and limitations

- Secrets are loaded from environment variables first, then `.env`.
- The workflow package does not modify the read-only reference scripts under `ComicBook/DoNotChange/`.
- No router, database, caching, or image API behavior is implemented yet.
- The package layout is intentionally reusable so later workflows can share the same contracts.

## Plain-language troubleshooting

If setup fails at this stage, the most likely cause is missing Azure configuration. The config loader raises a clear validation error listing the required variables that are absent.
