# Repository Reorganization

Developer notes for the phased migration from `ComicBook/comicbook/` to `workflows/pipelines/`.

## Current implementation status

- TG1: complete
- TG2: in progress (bootstrap + shared config/deps slice complete)
- TG3-TG5: not started

TG1 was kept intentionally narrow so the migration now has a tested shared logging foundation before package moves begin. The next slice established `workflows/` as the target-tree project root for migrated metadata and focused pytest scopes. The latest slice then moved the shared configuration and dependency-container modules into `pipelines.shared` and started the explicit `workflows/comicbook/` compatibility package.

## TG1 deliverables

The completed slice touched only the shared logging foundation plus its focused tests.

- `workflows/pipelines/shared/logging.py`
- `workflows/tests/shared/test_logging.py`

The logging module now supports and tests:

- required top-level fields for structured JSON output
- promoted optional fields such as `component`, `duration_ms`, and node context
- nested `extra` payloads for non-promoted fields
- promoted `error.code`, `error.message`, and `error.retryable` fields when callers pass an `error` mapping
- consistent exception serialization
- idempotent logger configuration
- opt-in text output through `PIPELINES_LOG_FORMAT=text`

## TG2 bootstrap deliverables

The current session kept TG2 intentionally small and foundational.

- added `workflows/pyproject.toml` so the target tree now carries package discovery and pytest configuration
- moved the shared environment template to `workflows/.env.example`
- updated setup-facing documentation and READMEs to point at the new environment-template path

## TG2 shared config/deps deliverables

The latest slice kept TG2 focused on one small vertical cut.

- moved `config.py` into `workflows/pipelines/shared/config.py`
- moved `deps.py` into `workflows/pipelines/shared/deps.py`
- added `workflows/comicbook/config.py` and `workflows/comicbook/deps.py` as the first target-tree compatibility wrappers
- converted `ComicBook/comicbook/config.py` and `ComicBook/comicbook/deps.py` into thin legacy wrappers so the old test/runtime entry points can still resolve the migrated shared modules during the transition
- added focused target-tree tests in `workflows/tests/shared/test_config_and_deps.py`

## Verification

Focused verification for the migrated target-tree test scope now runs from `workflows/` while still reusing the existing locked dependency environment from `ComicBook/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_logging.py tests/shared/test_config_and_deps.py
```

Legacy continuity for the moved shared modules was also checked from `ComicBook/`:

```bash
uv run --project "." --no-sync pytest -q tests/test_config.py
```

The `pythonpath = ["."]` pytest setting in `workflows/pyproject.toml` keeps the target package importable from the new root without extra shell setup. This keeps the slice install-free while proving that `workflows/pyproject.toml` can now drive the focused target-tree pytest scope.

## Important boundaries

The completed TG1 + TG2 bootstrap work does **not** yet:

- move runtime modules out of `ComicBook/comicbook/`
- rewire legacy runtime imports to `pipelines.shared.logging`
- add more than the first `config` / `deps` compatibility wrappers
- change workflow state ownership
- move the main legacy test suite out of `ComicBook/tests/`

Those changes remain sequenced behind TG2 and later TaskGroups in the implementation guide.

## Next expected slice

The next TG2 slice should continue the shared-runtime move with another bounded cluster that has its own focused test strategy, most likely `repo_protection.py` plus its script/tests or another similarly self-contained shared module group.

## Related documents

- [Planning and handoff](../../planning/repo-reorganization/index.md)
- [Business-facing status](../../business/repo-reorganization/index.md)
- [ADR-0002](../../planning/adr/ADR-0002-repo-reorganization.md)
