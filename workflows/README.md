# workflows/

This directory is the active repository root for the migrated multi-workflow Python package `pipelines`.

## Current repository state

The repo reorganization cleanup has landed. See `docs/planning/repo-reorganization/implementation-handoff.md` for the final TG5 verification status.

- shared infrastructure now lives under `workflows/pipelines/shared/`
- workflow runtime code now lives under `workflows/pipelines/workflows/image_prompt_gen/` and `workflows/pipelines/workflows/template_upload/`
- the canonical pytest tree now lives under `workflows/tests/`
- shared example assets live under `workflows/examples/`
- protected reference scripts live under `workflows/DoNotChange/`
- cross-workflow Responses helpers now live under `workflows/pipelines/shared/responses.py`
- cross-workflow metadata-backfill prompt/schema helpers now live under `workflows/pipelines/shared/metadata_backfill.py`
- non-node runtime logging is now standardized through `pipelines.shared.logging` and `log_event(...)`
- workflow doc slugs are normalized to `image-prompt-gen-workflow` and `template-upload-workflow`

## Local commands

Run these commands from `workflows/`.

### Full target-tree test suite

```bash
uv run --project "." --no-sync pytest -c pyproject.toml -q
```

### Focused workflow test scopes

```bash
uv run --project "." --no-sync pytest -c pyproject.toml -q tests/shared
uv run --project "." --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen
uv run --project "." --no-sync pytest -c pyproject.toml -q tests/template_upload
```

### CLI help smoke checks

```bash
uv run --project "." --no-sync python3 -m pipelines.workflows.image_prompt_gen.run --help
uv run --project "." --no-sync python3 -m pipelines.workflows.template_upload.run --help
```

## Important boundaries

- Do not reintroduce legacy `comicbook.*` compatibility shims.
- Do not add canonical tests outside `workflows/tests/`.
- Follow the active migration guide in [`docs/planning/repo-reorganization/implementation-v2.md`](../docs/planning/repo-reorganization/implementation-v2.md) for any reorganization work.
- The canonical repository layout lives in [`docs/standards/repo-structure.md`](../docs/standards/repo-structure.md).
- The canonical logging contract lives in [`docs/standards/logging-standards.md`](../docs/standards/logging-standards.md).
