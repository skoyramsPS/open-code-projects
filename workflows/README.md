# workflows/

This folder is the home for the multi-workflow Python package `pipelines`.

The repository is in the middle of a reorganization away from the legacy
`ComicBook/comicbook/` layout. After the current TG2 slices:

- `workflows/pyproject.toml` is now the target-tree project metadata, so focused
  pytest scopes for migrated code can run from this directory.
- `workflows/.env.example` is now the shared environment template for the
  migration.
- `pipelines/shared/` now owns the shared logging, configuration, and dependency
  container modules.
- `workflows/comicbook/` has started as the temporary explicit compatibility
  package for legacy imports while the rest of TG2 is still in progress.
- The live runtime code still mostly lives under `ComicBook/comicbook/`; most of
  the runtime and tests are still waiting to move.

The plan, the phases, and the import-shim strategy are documented in
[`docs/planning/repo-reorganization/plan.md`](../docs/planning/repo-reorganization/plan.md).
The target structure is canonical in
[`docs/standards/repo-structure.md`](../docs/standards/repo-structure.md).
The logging contract is canonical in
[`docs/standards/logging-standards.md`](../docs/standards/logging-standards.md).

Do not add files to `pipelines/` outside of what the active migration phase
calls for. New work targets the layout described in the standards.
