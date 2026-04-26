# Template Upload Workflow

## Status

- Workflow delivery status: implemented
- Repository layout status: fully migrated to `workflows/pipelines/`
- Current CLI module: `pipelines.workflows.template_upload.run`

## What this workflow does

This workflow imports style-template JSON into the shared SQLite template library.

It:

- validates each input row independently
- optionally backfills missing `tags` and `summary`
- inserts new templates or updates existing templates in place
- skips already completed rows when the same file is rerun
- writes a durable markdown report and structured log output

## Accepted inputs

- a JSON file path
- `--stdin` with the JSON payload piped in

Supported JSON shapes:

1. a top-level array of template rows
2. a `{ "version": 1, "templates": [...] }` envelope

Required row fields:

- `template_id`
- `name`
- `style_text`

## Outputs

- `runs/<import_run_id>/import_report.md`
- `logs/<import_run_id>.import.jsonl`
- SQLite audit rows in `import_runs` and `import_row_results`

## How to run it

Run from `workflows/`.

```bash
uv run --project "." --no-sync python -m pipelines.workflows.template_upload.run --allow-external-path ../docs/planning/template-upload-workflow/sample_input.json
uv run --project "." --no-sync python -m pipelines.workflows.template_upload.run --stdin < ../docs/planning/template-upload-workflow/sample_input.json
uv run --project "." --no-sync python -m pipelines.workflows.template_upload.run --dry-run --allow-external-path ../docs/planning/template-upload-workflow/sample_input.json
```

## Important behavior

- incoming `created_by_run` values are ignored and replaced with `workflow_import`
- `tags: []` is treated as intentional, not missing
- unresolved `supersedes_id` targets degrade to warnings instead of hard failures
- the backfill budget guard applies only to estimated metadata-backfill cost for the current import run

## Troubleshooting

Common issues:

- malformed top-level JSON shape
- missing required row fields
- disabled backfill without allowing missing optional fields
- import-lock contention on the selected SQLite database

For maintainer details, see `docs/developer/template-upload-workflow/index.md`.
