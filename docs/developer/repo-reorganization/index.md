# Repository Reorganization

Developer notes for the phased migration from `ComicBook/comicbook/` to `workflows/pipelines/`.

## Current implementation status

- TG1: complete
- TG2-TG5: not started

TG1 was kept intentionally narrow so the migration now has a tested shared logging foundation before package moves begin.

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

## Verification

Focused verification for TG1 runs from the repository root while pointing Python at the target tree:

```bash
PYTHONPATH=workflows uv run --project "ComicBook" --no-sync pytest -q workflows/tests/shared/test_logging.py
```

This keeps TG1 narrow while `workflows/` is still a staged target tree rather than the active package root.

## Important boundaries

TG1 does **not** yet:

- move runtime modules out of `ComicBook/comicbook/`
- rewire legacy runtime imports to `pipelines.shared.logging`
- add compatibility wrappers
- change workflow state ownership

Those changes remain sequenced behind TG2 and later TaskGroups in the implementation guide.

## Next expected slice

TG2 should make `workflows/` the active runtime root, move package/test assets, and introduce the temporary `comicbook` compatibility package.

## Related documents

- [Planning and handoff](../../planning/repo-reorganization/index.md)
- [Business-facing status](../../business/repo-reorganization/index.md)
- [ADR-0002](../../planning/adr/ADR-0002-repo-reorganization.md)
