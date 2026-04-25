# workflows/

This folder is the home for the multi-workflow Python package `pipelines`.

The repository is in the middle of a reorganization away from the legacy
`ComicBook/comicbook/` layout. Until the migration phases land:

- The runtime code still lives under `ComicBook/comicbook/`. Tests, the CLI, and
  agents continue to operate against that location.
- This folder holds the **target** layout and the first piece of new code: the
  shared logging module at `pipelines/shared/logging.py`.

The plan, the phases, and the import-shim strategy are documented in
[`docs/planning/repo-reorganization/plan.md`](../docs/planning/repo-reorganization/plan.md).
The target structure is canonical in
[`docs/standards/repo-structure.md`](../docs/standards/repo-structure.md).
The logging contract is canonical in
[`docs/standards/logging-standards.md`](../docs/standards/logging-standards.md).

Do not add files to `pipelines/` outside of what the active migration phase
calls for. New work targets the layout described in the standards.
