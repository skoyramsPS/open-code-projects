# Template Upload Workflow

## Status

- Workflow delivery status: implemented with mocked verification complete
- Last updated: 2026-04-24
- Latest mocked validation result: `113 passed`
- Live Azure smoke status: not run in this session; keep it as an explicit opt-in step before spending real quota

## What this workflow does

This workflow imports art-style templates from JSON into the ComicBook project's SQLite template library.

In plain terms, it lets an operator hand the system a JSON file of templates and have the workflow:

- validate each row independently
- optionally fill in missing `tags` and `summary` metadata with the existing Azure-backed LLM route
- insert brand-new templates
- update existing templates in place when the same `template_id` already exists
- skip already completed rows when the same file is rerun
- write a durable report and structured log for the run

The workflow is intentionally row-by-row and resumable. One bad row should not destroy progress on the rest of the file.

## What operators provide

Operators can provide input in either of these ways:

- a JSON file path
- `--stdin` with the JSON payload piped in

Accepted JSON shapes:

1. a bare top-level array of template objects
2. a versioned envelope shaped like:

```json
{
  "version": 1,
  "templates": []
}
```

Required fields per template row:

- `template_id`
- `name`
- `style_text`

Optional fields:

- `tags`
- `summary`
- `created_at`
- `created_by_run` (ignored and replaced)
- `supersedes_id`

Important operator rule:

- incoming `created_by_run` is always ignored and replaced with `workflow_import`

## What the workflow does automatically

For every row, the workflow:

- validates required fields and keeps row-level failures isolated
- preserves intentional `tags: []` without forcing a backfill
- backfills missing or `null` `tags`, plus missing or blank `summary`, unless backfill is disabled
- stamps `created_at` when the input omits it
- treats `template_id` as the insert-vs-update key
- records row-level status so reruns of the same file hash can skip already completed rows
- writes update diffs when an existing template row changes
- downgrades an unresolved `supersedes_id` target to a warning and stores `NULL` instead of failing the row

Terminal row outcomes you may see in reports:

- `inserted`
- `updated`
- `skipped_duplicate`
- `skipped_resume`
- `failed`
- `dry_run_ok`

Run-level outcomes you may see on stdout or in the database:

- `succeeded`
- `partial`
- `dry_run`
- `failed`

## Outputs you can expect

The workflow writes:

- markdown report: `runs/<import_run_id>/import_report.md`
- structured log: `logs/<import_run_id>.import.jsonl`
- SQLite audit rows in the import tracking tables

The CLI also prints a small JSON object with:

- `import_run_id`
- `run_status`
- `report_path`

## How to run it

Work from the `ComicBook/` directory.

Example using the checked-in sample file by path:

```bash
uv run python -m comicbook.upload_run \
  --allow-external-path \
  ../docs/planning/template-upload-workflow/sample_input.json
```

Example using stdin:

```bash
uv run python -m comicbook.upload_run --stdin \
  < ../docs/planning/template-upload-workflow/sample_input.json
```

Example dry run without writing templates:

```bash
uv run python -m comicbook.upload_run \
  --dry-run \
  --allow-external-path \
  ../docs/planning/template-upload-workflow/sample_input.json
```

Example offline validation when backfill must stay disabled:

```bash
uv run python -m comicbook.upload_run \
  --no-backfill \
  --allow-missing-optional \
  path/to/templates.json
```

Supported operator flags:

- `--stdin`
- `--dry-run`
- `--no-backfill`
- `--allow-missing-optional` (valid only with `--no-backfill`)
- `--budget-usd <amount>`
- `--redact-style-text-in-logs`
- `--allow-external-path`

## Safety rules and limitations

- Only one template-import run can actively hold the import lock for a given SQLite database at a time.
- Template-import locking is separate from the image-generation workflow lock, so the two workflow families can coexist.
- The budget guard applies only to estimated metadata-backfill spend for the current import run.
- Row-level failures do not automatically make the whole run fail; they usually produce a `partial` run result instead.
- External file paths are blocked by default. Use `--allow-external-path` only when you intentionally want to read outside the current working tree.
- `tags: []` is treated as an intentional empty list, not missing metadata.
- `created_by_run` from the input file is never trusted.
- Update-in-place can change `style_text_hash`, so older prompt fingerprints may no longer describe the current template text exactly.
- Live Azure smoke validation is not part of the default mocked verification evidence.

## Plain-language troubleshooting

Common failure or surprise cases:

- **"top-level JSON value must be an array..."** — the file is not a supported array or `{version: 1, templates: [...]}` envelope.
- **Missing required field failures** — one row is missing `template_id`, `name`, or `style_text`; the run continues, but that row is marked failed.
- **`backfill_disabled`** — a row needed `tags` or `summary`, but you ran with `--no-backfill` and did not also allow missing optional values.
- **`budget_exceeded`** — the estimated remaining metadata-backfill spend would go over the chosen run budget.
- **`skipped_resume`** — the same file hash and row index already finished successfully in an earlier run, so the workflow reused prior progress.
- **Import lock error** — another import run is already active for the same database file.
- **External path rejection** — the file resolved outside the current working tree; rerun with `--allow-external-path` only if that is intentional.
- **Unresolved supersedes warning** — the requested `supersedes_id` target still did not exist after the retry pass, so the row was stored with `NULL` and a warning.

If you need the implementation details, persistence rules, or test commands, use the matching developer doc at `docs/developer/template-upload-workflow/index.md`.
