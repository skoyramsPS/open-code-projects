# Repository Reorganization

Plain-language status and operator-facing notes for the repository move into the `workflows/pipelines/` layout.

## What changed in TG1

The first implementation slice delivered the shared logging foundation in the target tree.

- `workflows/pipelines/shared/logging.py` is now the intended single logging module for the migrated runtime
- log output defaults to machine-readable JSON
- developers can opt into text logs locally with `PIPELINES_LOG_FORMAT=text`
- focused tests now cover formatter behavior, helper behavior, and duplicate-handler protection

## What has not changed yet

TG1 does **not** move the live runtime into `workflows/`.

- the active runtime still lives under `ComicBook/comicbook/`
- existing workflow commands and runtime paths are unchanged for operators
- no production workflow has been rewired to the new logger yet

That means this slice is a foundation change, not an operator rollout change.

## Why this matters

The migration will eventually place multiple workflows under one package. Before that move can be safe, the repository needs one logging format that works the same way across workflows and shared infrastructure.

TG1 establishes that shared contract first so later migration steps can adopt it without introducing a second logging implementation.

## Current rollout status

- TG1: complete
- TG2-TG5: not started

## Related documents

- [Planning and execution guide](../../planning/repo-reorganization/index.md)
- [Developer notes](../../developer/repo-reorganization/index.md)
- [Logging standards](../../standards/logging-standards.md)
