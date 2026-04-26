# workflows/

This directory is the active repository root for the migrated multi-workflow Python package `pipelines`.

## Current migration state

TG2 of the repository reorganization is complete.

- shared infrastructure now lives under `workflows/pipelines/shared/`
- workflow runtime code now lives under `workflows/pipelines/workflows/image_prompt_gen/` and `workflows/pipelines/workflows/template_upload/`
- the canonical pytest tree now lives under `workflows/tests/`
- shared example assets live under `workflows/examples/`
- protected reference scripts live under `workflows/DoNotChange/`
- `workflows/comicbook/` and `ComicBook/comicbook/` remain temporary compatibility layers while later TaskGroups finish the migration
- non-node runtime logging is now standardized through `pipelines.shared.logging` and `log_event(...)`
- the image workflow documentation slug is normalized to `image-prompt-gen-workflow` across planning, business, and developer docs

## Local commands

Run these commands from `workflows/`.

### Full target-tree test suite

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q
```

### Focused workflow test scopes

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload
```

### CLI help smoke checks

```bash
uv run --project "../ComicBook" --no-sync python3 -m pipelines.workflows.image_prompt_gen.run --help
uv run --project "../ComicBook" --no-sync python3 -m pipelines.workflows.template_upload.run --help
```

## Important boundaries

- Do not add new source-of-truth runtime modules under `ComicBook/comicbook/`; that tree is compatibility-only during the shim window.
- Do not add new canonical tests under `ComicBook/tests/`; use `workflows/tests/`.
- Follow the active migration guide in [`docs/planning/repo-reorganization/implementation-v2.md`](../docs/planning/repo-reorganization/implementation-v2.md) for any reorganization work.
- The canonical repository layout lives in [`docs/standards/repo-structure.md`](../docs/standards/repo-structure.md).
- The canonical logging contract lives in [`docs/standards/logging-standards.md`](../docs/standards/logging-standards.md).
