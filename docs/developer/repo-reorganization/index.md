# Repository Reorganization

Developer notes for the phased migration from `ComicBook/comicbook/` to `workflows/pipelines/`.

## Current implementation status

- TG1: complete
- TG2: in progress (bootstrap + shared config/deps + repo-protection + fingerprint + db + execution + runtime-deps + CLI entry-point slices complete)
- TG3-TG5: not started

TG1 was kept intentionally narrow so the migration now has a tested shared logging foundation before package moves begin. The next slice established `workflows/` as the target-tree project root for migrated metadata and focused pytest scopes. The following slice then moved the shared configuration and dependency-container modules into `pipelines.shared` and started the explicit `workflows/comicbook/` compatibility package. The next slice moved the repo-protection helper into `pipelines.shared` and kept the legacy script/import surface working through wrappers. The following slice moved the fingerprint helper into `pipelines.shared` and kept both target-tree and legacy imports working while state ownership is still waiting on TG3. The next slice moved the SQLite DAO into `pipelines.shared` and kept both target-tree and legacy imports working through the same thin-wrapper pattern. The next slice moved the reusable graph-execution helpers into `pipelines.shared` and kept both target-tree and legacy imports working with a temporary fallback for the still-legacy ingest/state dependencies. The next slice moved `runtime_deps.py` into `pipelines.shared`, switched managed dependency construction to the shared logger factory, and preserved both the legacy `comicbook.runtime_deps` import path and the package-root `upload_templates` convenience export. The latest slice moved the workflow CLI entry points into `pipelines.workflows.image_prompt_gen.run` and `pipelines.workflows.template_upload.run`, adopted `log_event(...)` in those non-node entry points, and changed the `comicbook.run` / `comicbook.upload_run` compatibility surface from plain re-exports to module aliases so monkeypatch-heavy tests keep working.

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

## TG2 repo-protection deliverables

The newest slice kept TG2 bounded to one more shared module plus its focused verification path.

- moved `repo_protection.py` into `workflows/pipelines/shared/repo_protection.py`
- added `workflows/comicbook/repo_protection.py` as the target-tree compatibility wrapper
- converted `ComicBook/comicbook/repo_protection.py` into a thin legacy wrapper so `ComicBook/scripts/check_do_not_change.py` can keep importing the same public surface during TG2
- added focused target-tree coverage in `workflows/tests/shared/test_repo_protection.py` for the shared module, wrapper identity, and the legacy CLI script path

## TG2 fingerprint deliverables

The newest slice kept TG2 on the same one-shared-module-at-a-time pattern.

- moved `fingerprint.py` into `workflows/pipelines/shared/fingerprint.py`
- added `workflows/comicbook/fingerprint.py` as the next target-tree compatibility wrapper
- converted `ComicBook/comicbook/fingerprint.py` into a thin legacy wrapper so the old import surface still resolves the migrated helper
- added focused target-tree coverage in `workflows/tests/shared/test_fingerprint.py`
- kept the moved helper importable from the target tree by using a temporary fallback to the legacy `RenderedPrompt` model until TG3 relocates state ownership

## TG2 database deliverables

The newest slice kept TG2 on the same one-shared-module-at-a-time pattern while moving a more connected persistence helper.

- moved `db.py` into `workflows/pipelines/shared/db.py`
- added `workflows/comicbook/db.py` as the next target-tree compatibility wrapper
- converted `ComicBook/comicbook/db.py` into a thin legacy wrapper so the old import surface still resolves the migrated DAO
- added focused target-tree coverage in `workflows/tests/shared/test_db.py`
- kept the moved helper importable from the target tree by using a temporary fallback to the legacy `TemplateSummary` model until TG3 relocates state ownership

## TG2 execution deliverables

The newest slice kept TG2 on the same one-shared-module-at-a-time pattern while moving the shared orchestration helpers used by multiple workflow entry points.

- moved `execution.py` into `workflows/pipelines/shared/execution.py`
- added `workflows/comicbook/execution.py` as the next target-tree compatibility wrapper
- converted `ComicBook/comicbook/execution.py` into a thin legacy wrapper so the old import surface still resolves the migrated helper
- added focused target-tree coverage in `workflows/tests/shared/test_execution.py`
- kept the moved helper importable from the target tree by using a temporary fallback to the legacy ingest/state modules until TG3 and later TG2 wrapper work relocate those dependencies cleanly

## TG2 runtime-deps deliverables

The newest slice kept TG2 on the same one-shared-module-at-a-time pattern while moving the managed runtime-construction helper used by both workflow entry points.

- moved `runtime_deps.py` into `workflows/pipelines/shared/runtime_deps.py`
- added `workflows/comicbook/runtime_deps.py` as the next target-tree compatibility wrapper
- converted `ComicBook/comicbook/runtime_deps.py` into a thin legacy wrapper so the old import surface still resolves the migrated helper
- changed managed dependency construction to use `get_logger(__name__)` from the shared logging module
- kept default pricing resolution working without a file move by falling back to the legacy `ComicBook/comicbook/pricing.json` asset until later TG2 workflow-asset work lands
- updated `workflows/comicbook/__init__.py` so the target-tree compatibility package preserves the legacy package-root `upload_templates` re-export that existing tests expect
- added focused target-tree coverage in `workflows/tests/shared/test_runtime_deps.py`, including the package-root `upload_templates` re-export

## TG2 CLI entry-point deliverables

The newest slice kept TG2 focused on the two runtime entry points that sit on top of the already moved shared helpers.

- moved the image workflow entry point into `workflows/pipelines/workflows/image_prompt_gen/run.py`
- moved the template-upload entry point into `workflows/pipelines/workflows/template_upload/run.py`
- added `workflows/comicbook/run.py` and `workflows/comicbook/upload_run.py` as target-tree compatibility aliases to those moved modules
- converted `ComicBook/comicbook/run.py` and `ComicBook/comicbook/upload_run.py` into legacy compatibility aliases so existing importers and monkeypatch-based tests now point at the moved source-of-truth modules
- adopted `log_event(...)` for batch progress, single-run lifecycle, import-run lifecycle, and CLI error handling in the moved entry points
- added `workflows/comicbook/input_file.py` so the moved image entry point can still resolve the existing input-file helper from the target tree without pulling TG3 state work forward
- added focused target-tree coverage in `workflows/tests/image_prompt_gen/test_run.py` and `workflows/tests/template_upload/test_run.py`

## Verification

Focused verification for the migrated target-tree test scope now runs from `workflows/` while still reusing the existing locked dependency environment from `ComicBook/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_logging.py tests/shared/test_runtime_deps.py tests/image_prompt_gen/test_run.py tests/template_upload/test_run.py
```

Legacy continuity for the moved shared modules and runtime entry points was also checked from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_budget_guard.py tests/test_input_file_support.py tests/test_upload_run_cli.py
```

The `pythonpath = ["."]` pytest setting in `workflows/pyproject.toml` keeps the target package importable from the new root without extra shell setup. This keeps the slice install-free while proving that `workflows/pyproject.toml` can now drive the focused target-tree pytest scope.

The target-tree compatibility aliases were also checked directly from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync python - <<'PY'
from comicbook import upload_templates as package_upload_templates
from comicbook.run import run_once as wrapped_run_once
from pipelines.workflows.image_prompt_gen.run import run_once as moved_run_once
from pipelines.workflows.template_upload.run import upload_templates as moved_upload_templates
print(package_upload_templates is moved_upload_templates)
print(wrapped_run_once is moved_run_once)
PY
```

## Important boundaries

The completed TG1 + TG2 bootstrap work does **not** yet:

- move runtime modules out of `ComicBook/comicbook/`
- move most workflow-owned modules such as graphs, nodes, prompts, adapters, and state out of `ComicBook/comicbook/`
- let the moved entry points execute entirely through target-tree workflow modules without still relying on legacy workflow-module bridges
- add more than the current `config` / `deps` / `repo_protection` / `fingerprint` / `db` / `execution` / `runtime_deps` / `input_file` / `run` / `upload_run` compatibility wrappers
- change workflow state ownership
- move the main legacy test suite out of `ComicBook/tests/`

Those changes remain sequenced behind TG2 and later TaskGroups in the implementation guide.

## Next expected slice

The next TG2 slice should continue from the moved entry points into the remaining workflow-local bridges they still depend on, most likely `graph.py`, `upload_graph.py`, and the minimum target-tree compatibility scaffolding needed for those modules, while still leaving node moves and TG3 state splitting untouched.

## Related documents

- [Planning and handoff](../../planning/repo-reorganization/index.md)
- [Business-facing status](../../business/repo-reorganization/index.md)
- [ADR-0002](../../planning/adr/ADR-0002-repo-reorganization.md)
