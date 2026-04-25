# workflows/

This folder is the home for the multi-workflow Python package `pipelines`.

The repository is in the middle of a reorganization away from the legacy
`ComicBook/comicbook/` layout. After the current TG2 slices:

- `workflows/pyproject.toml` is now the target-tree project metadata, so focused
  pytest scopes for migrated code can run from this directory.
- `workflows/.env.example` is now the shared environment template for the
  migration.
- `pipelines/shared/` now owns the shared logging, configuration, dependency
  container, repo-protection, fingerprint, database, execution-helper, and
  runtime-deps modules.
- `workflows/comicbook/` has started as the temporary explicit compatibility
  package for legacy imports while the rest of TG2 is still in progress.
- the legacy `ComicBook/scripts/check_do_not_change.py` entry point still works
  through the migrated `repo_protection` wrapper chain, while the protected path
  remains `ComicBook/DoNotChange` until that asset moves later in TG2.
- prompt fingerprinting helpers now also resolve from the target tree through
  `pipelines/shared/fingerprint.py`, with a temporary fallback to the legacy
  state model until TG3 moves state ownership.
- the SQLite DAO now also resolves from the target tree through
  `pipelines/shared/db.py`, with a temporary fallback to the legacy
  `TemplateSummary` model until TG3 moves state ownership cleanly.
- graph execution helpers now also resolve from the target tree through
  `pipelines/shared/execution.py`, with a temporary fallback to the legacy
  ingest/state modules until TG3 and later TG2 wrapper work move those
  dependencies cleanly.
- managed runtime dependency construction now also resolves from the target tree
  through `pipelines/shared/runtime_deps.py`, uses the shared logger factory,
  and temporarily falls back to the legacy `ComicBook/comicbook/pricing.json`
  asset until the workflow-specific pricing file moves later in TG2.
- the workflow CLI entry points now live under
  `pipelines/workflows/image_prompt_gen/run.py` and
  `pipelines/workflows/template_upload/run.py`.
- the workflow graph modules now also live under
  `pipelines/workflows/image_prompt_gen/graph.py` and
  `pipelines/workflows/template_upload/graph.py`.
- both `workflows/comicbook/` and `ComicBook/comicbook/` now expose `run` and
  `upload_run` as compatibility aliases to those moved modules, so old imports
  and monkeypatch-based tests still point at the same module objects.
- both `workflows/comicbook/` and `ComicBook/comicbook/` now also expose
  `graph` and `upload_graph` as compatibility aliases to the moved graph
  modules.
- those moved entry points now emit structured `log_event(...)` records directly
  for run lifecycle, batch lifecycle, import lifecycle, and CLI error cases.
- the moved entry points now call the moved target-tree graph modules directly
  instead of routing back through the legacy graph modules.
- `workflows/comicbook/__init__.py` now preserves the legacy package-root
  `upload_templates` re-export and extends the compatibility package path to the
  still-legacy `ComicBook/comicbook/` tree so unmoved workflow-local modules can
  still resolve during TG2.
- `workflows/comicbook/input_file.py` now keeps the moved image run module
  importable from the target tree without moving input-file parsing ownership
  yet.
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
