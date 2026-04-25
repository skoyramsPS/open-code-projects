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
- TG2 has now moved `runtime_deps.py` into `workflows/pipelines/shared/`, added matching target-tree and legacy compatibility wrappers, switched managed dependency construction to `get_logger(__name__)`, and kept default pricing resolution working through a temporary fallback to the legacy `ComicBook/comicbook/pricing.json` file until the workflow asset move lands.
- `workflows/comicbook/__init__.py` now preserves the legacy package-root `upload_templates` re-export so the growing compatibility package keeps matching the old convenience import surface.
- The broader TG2 workflow-module move, full CLI `log_event(...)` adoption, test move, and remaining `comicbook` compatibility-wrapper work are still pending.
