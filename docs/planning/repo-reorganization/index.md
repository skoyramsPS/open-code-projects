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
- TG2 is the next queued TaskGroup: move the active runtime and tests into `workflows/` with temporary `comicbook` compatibility wrappers.
