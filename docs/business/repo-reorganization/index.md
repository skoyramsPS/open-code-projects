# Repository Reorganization

Plain-language status and operator-facing notes for the repository move into the `workflows/pipelines/` layout.

## What changed so far

Three migration slices have landed so far.

### TG1 foundation

- `workflows/pipelines/shared/logging.py` is now the intended single logging module for the migrated runtime
- log output defaults to machine-readable JSON
- developers can opt into text logs locally with `PIPELINES_LOG_FORMAT=text`
- focused tests now cover formatter behavior, helper behavior, and duplicate-handler protection

### TG2 bootstrap

- `workflows/pyproject.toml` now makes `workflows/` the intended project root for migrated code and target-tree pytest scopes
- `workflows/.env.example` is now the shared environment-template path that operators and developers should copy from when preparing local configuration

### TG2 shared-config/deps move

- the shared configuration and dependency-container modules now live under `workflows/pipelines/shared/`
- the target tree now includes the first explicit `workflows/comicbook/` compatibility wrappers for legacy `comicbook.config` and `comicbook.deps` imports
- legacy tests still pass for the moved configuration surface, so this slice changes module ownership without changing operator behavior

## What has not changed yet

The TG2 bootstrap slice does **not** move the live runtime into `workflows/`.

- the active runtime still lives under `ComicBook/comicbook/`
- existing workflow commands and runtime paths are unchanged for operators
- no production workflow has been rewired to the new logger yet
- only the first temporary `comicbook` compatibility wrappers exist so far; most legacy import paths are still pending migration

That means the migration has updated project metadata and configuration guidance,
but it has not rolled the runtime itself over to the new package tree yet.

## Why this matters

The migration will eventually place multiple workflows under one package. Before that move can be safe, the repository needs one logging format that works the same way across workflows and shared infrastructure.

TG1 establishes that shared contract first so later migration steps can adopt it without introducing a second logging implementation.

## Current rollout status

- TG1: complete
- TG2: in progress (bootstrap + shared config/deps slice complete)
- TG3-TG5: not started

## Related documents

- [Planning and execution guide](../../planning/repo-reorganization/index.md)
- [Developer notes](../../developer/repo-reorganization/index.md)
- [Logging standards](../../standards/logging-standards.md)
