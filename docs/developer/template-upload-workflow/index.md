# Template Upload Workflow

## Status

- Workflow delivery status: implemented
- Repository layout status: fully migrated to `workflows/pipelines/`
- Canonical runtime package: `pipelines.workflows.template_upload`

## Runtime surface

- CLI entry point: `python -m pipelines.workflows.template_upload.run`
- library helper: `from pipelines.workflows.template_upload.run import upload_templates`
- graph assembly: `pipelines.workflows.template_upload.graph`
- state contract: `pipelines.workflows.template_upload.state`

## Graph order

The compiled graph runs:

1. `load_file`
2. `parse_and_validate`
3. `resume_filter`
4. `backfill_metadata`
5. `decide_write_mode`
6. `persist`
7. conditional deferred-retry preparation
8. `decide_write_mode` again for deferred rows
9. `persist` again for deferred rows
10. `summarize`

## Shared-module promotions used by this workflow

- `pipelines.shared.metadata_backfill` owns the reusable metadata-backfill prompt/schema helpers
- `pipelines.shared.responses` owns the reusable structured Responses transport helpers

## State contract highlights

Workflow-owned types live in `pipelines.workflows.template_upload.state`, including:

- `ImportRunState`
- `TemplateImportRow`
- `TemplateImportRowResult`
- `ImportRowStatus`
- `ImportWriteMode`

Shared base types such as `UsageTotals` and `WorkflowError` live in `pipelines.shared.state`.

## Persistence notes

Upload-specific persistence uses `pipelines.shared.db.ComicBookDB`.

Important helpers:

- `acquire_import_lock(...)`
- `finalize_import_run(...)`
- `record_import_row_result(...)`
- `get_template_by_id(...)`
- `update_template_in_place(...)`
- `count_prompt_rows_for_template_hash(...)`

## Commands

Run from `workflows/`.

```bash
uv run --project "." --no-sync python -m pipelines.workflows.template_upload.run --help
uv run --project "." --no-sync pytest -c pyproject.toml -q tests/template_upload
```

## Maintenance notes

- keep node logging on `log_node_event(...)`
- do not reintroduce `upload_` prefixes in the target-tree runtime node names
- do not reintroduce `comicbook.*` imports or shim-style wrappers
- promote any additional cross-workflow helper into `pipelines.shared/`

For operator-facing usage, see `docs/business/template-upload-workflow/index.md`.
