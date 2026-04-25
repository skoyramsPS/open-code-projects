# Repository Reorganization

Planning material for moving the repository from a flat single-package layout to a per-workflow layout under `workflows/pipelines/` with a shared logging standard.

## Documents

- [Reorganization plan](plan.md)
- [Implementation guide](implementation.md)
- [Implementation handoff](implementation-handoff.md)

## Related

- [ADR-0002: Reorganize the repository into a multi-workflow `pipelines` package with a shared logging standard](../adr/ADR-0002-repo-reorganization.md)
- [Business status](../../business/repo-reorganization/index.md)
- [Developer notes](../../developer/repo-reorganization/index.md)
- [Repository structure standards](../../standards/repo-structure.md)
- [Logging standards](../../standards/logging-standards.md)

## Status

Implementation is in progress.

- TG1 is complete: the shared logging foundation in `workflows/pipelines/shared/logging.py` is now covered by focused tests.
- TG2 has started with a bootstrap slice: `workflows/pyproject.toml` now defines the target-tree project metadata and `workflows/.env.example` now holds the shared environment template.
- TG2 has now started the shared-module move: `config.py`, `deps.py`, `repo_protection.py`, `fingerprint.py`, `db.py`, `execution.py`, and `runtime_deps.py` live under `workflows/pipelines/shared/`, and temporary `workflows/comicbook/` compatibility wrappers now exist for those modules.
- TG2 has now moved the workflow CLI entry points into `workflows/pipelines/workflows/image_prompt_gen/run.py` and `workflows/pipelines/workflows/template_upload/run.py`.
- Both target-tree and legacy `comicbook.run` / `comicbook.upload_run` paths now resolve through module-alias wrappers, which keeps monkeypatching and existing test behavior intact while the source of truth lives under `pipelines.workflows.*`.
- The moved CLI and library entry points now emit structured `log_event(...)` records directly for batch progress, single-run lifecycle events, import-run lifecycle events, and CLI error handling.
- TG2 has now moved the workflow graph modules into `workflows/pipelines/workflows/image_prompt_gen/graph.py` and `workflows/pipelines/workflows/template_upload/graph.py`.
- Both target-tree and legacy `comicbook.graph` / `comicbook.upload_graph` paths now resolve through module-alias wrappers, so the moved entry points execute through the target-tree graph modules while monkeypatch behavior stays intact.
- `workflows/comicbook/__init__.py` still preserves the legacy package-root `upload_templates` re-export, now extends the compatibility package path to the still-legacy `ComicBook/comicbook/` tree, and `workflows/comicbook/input_file.py` still keeps the moved image entry point importable from the target tree without moving input-file parsing ownership yet.
- The broader TG2 workflow-helper, node, test, and remaining `comicbook` compatibility-wrapper work are still pending.
