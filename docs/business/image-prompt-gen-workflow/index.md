# Image Prompt Generation Workflow

## Status

- Workflow delivery status: implemented
- Repository layout status: fully migrated to `workflows/pipelines/`
- Current CLI module: `pipelines.workflows.image_prompt_gen.run`

## What this workflow does

This workflow turns a prompt, or a JSON/CSV batch of prompts, into one or more generated images.

In plain terms, it:

- loads the saved template catalog
- asks the router model to choose or compose the right prompt plan
- optionally persists a newly extracted template before image generation
- reuses cached images when the same prompt fingerprint already exists
- generates remaining images serially
- writes a markdown report plus a structured summary for each run

## Inputs operators can provide

- a direct prompt string
- `--input-file` pointing at a JSON or CSV prompt file
- optional controls such as `--dry-run`, `--force`, `--panels`, `--budget-usd`, `--run-id`, and `--redact-prompts`

The supported local environment shape is documented in `workflows/.env.example`.

## Outputs you can expect

- generated images under `image_output/<run_id>/`
- run reports under `runs/<run_id>/report.md`
- structured summaries under `logs/<run_id>.summary.json`
- SQLite records for runs, prompts, images, and templates

## How to run it

Run from `workflows/`.

```bash
uv run --project "." --no-sync python -m pipelines.workflows.image_prompt_gen.run "A heroic portrait at dawn"
uv run --project "." --no-sync python -m pipelines.workflows.image_prompt_gen.run --input-file examples/prompts.sample.json
uv run --project "." --no-sync python -m pipelines.workflows.image_prompt_gen.run --input-file examples/prompts.sample.csv --dry-run
```

## Guardrails and limits

- image generation is serial, not parallelized
- large template catalogs are prefiltered before routing
- budget guards can stop a run before image generation begins
- cache reuse is on by default unless `--force` is passed
- live Azure smoke validation remains an explicit opt-in activity outside the default mocked regression suite

## Troubleshooting

Common failure cases:

- missing Azure config values
- a lock already held for the selected SQLite database
- invalid router output after the allowed repair attempt
- malformed JSON/CSV prompt files
- budget or rate-limit protection intentionally stopping generation

For maintainer details, see `docs/developer/image-prompt-gen-workflow/index.md`.
