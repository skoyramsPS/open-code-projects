# Repository Reorganization

Plain-language status and operator-facing notes for the repository move into the `workflows/pipelines/` layout.

## What changed so far

Twelve migration slices have landed so far.

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

### TG2 repo-protection move

- the repo-protection helper now lives under `workflows/pipelines/shared/repo_protection.py`
- the target tree now also exposes `workflows/comicbook/repo_protection.py` so migrated code and temporary legacy imports share one implementation
- the legacy `ComicBook/scripts/check_do_not_change.py` script path still works, and the protected path remains `ComicBook/DoNotChange` until that asset moves later in TG2

### TG2 fingerprint move

- the fingerprint helper now lives under `workflows/pipelines/shared/fingerprint.py`
- the target tree now also exposes `workflows/comicbook/fingerprint.py` so legacy `comicbook.fingerprint` imports keep working during the migration
- prompt fingerprinting and rendered-prompt materialization behavior is unchanged in tests, even though the underlying helper module now lives in the target tree

### TG2 database move

- the shared SQLite DAO now lives under `workflows/pipelines/shared/db.py`
- the target tree now also exposes `workflows/comicbook/db.py` so legacy `comicbook.db` imports keep working during the migration
- database behavior is unchanged in focused persistence tests and representative legacy workflow smoke tests, even though the underlying module now lives in the target tree

### TG2 execution-helper move

- the shared graph-execution helpers now live under `workflows/pipelines/shared/execution.py`
- the target tree now also exposes `workflows/comicbook/execution.py` so legacy `comicbook.execution` imports keep working during the migration
- workflow orchestration behavior is unchanged in focused helper tests and representative legacy workflow smoke tests, even though the underlying helper module now lives in the target tree

### TG2 runtime-deps move

- the managed runtime-dependency helper now lives under `workflows/pipelines/shared/runtime_deps.py`
- the target tree now also exposes `workflows/comicbook/runtime_deps.py` so legacy `comicbook.runtime_deps` imports keep working during the migration
- managed dependency construction now gets its logger from the shared logging foundation, while default pricing lookup still falls back to the legacy `ComicBook/comicbook/pricing.json` asset until that file moves later in TG2
- representative legacy runtime-entrypoint tests still pass, so this slice changes helper ownership and logger construction without changing operator commands

### TG2 CLI entry-point move

- the image and template-upload CLI entry points now live under `workflows/pipelines/workflows/image_prompt_gen/run.py` and `workflows/pipelines/workflows/template_upload/run.py`
- both `workflows/comicbook/` and `ComicBook/comicbook/` now expose `run` and `upload_run` as compatibility aliases to the moved modules, so existing imports and monkeypatch-based tests still behave the same way
- the moved entry points now emit structured `log_event(...)` records directly for run lifecycle, batch lifecycle, import lifecycle, and CLI error cases
- operators still use the same command surface today because the compatibility layer keeps the legacy import paths working while TG2 continues

### TG2 workflow-graph move

- the image and template-upload workflow graph modules now live under `workflows/pipelines/workflows/image_prompt_gen/graph.py` and `workflows/pipelines/workflows/template_upload/graph.py`
- both `workflows/comicbook/` and `ComicBook/comicbook/` now expose `graph` and `upload_graph` as compatibility aliases to those moved modules, so existing imports and monkeypatch-style test behavior still work
- the moved entry points now call the moved target-tree graph modules directly, while still relying on temporary legacy-module fallback for nodes, prompts, adapters, and state that have not moved yet

### TG2 image-helper-module move

- the image-workflow helper modules now live under `workflows/pipelines/workflows/image_prompt_gen/`, including input-file parsing, router prompt/schema helpers, metadata-backfill prompt/schema helpers, router transport helpers, and the image client adapter
- the default pricing asset now also lives under `workflows/pipelines/workflows/image_prompt_gen/pricing.json`
- both `workflows/comicbook/` and `ComicBook/comicbook/` now expose `input_file`, `router_prompts`, `metadata_prompts`, `router_llm`, and `image_client` as compatibility aliases to the moved modules, so existing imports and monkeypatch-based tests still behave the same way

### TG2 state-and-node wrapper move

- the target-tree compatibility package now includes explicit `comicbook.state` and `comicbook.nodes.*` wrappers for the still-legacy state module and node modules used by the moved graph layer
- the moved graph layer no longer relies on the old `ComicBook/comicbook` package-path fallback inside `workflows/comicbook/__init__.py`
- operator commands are still unchanged, but the target-tree compatibility surface is now more explicit and less dependent on import-path magic

## What has not changed yet

TG2 has not finished moving the live runtime into `workflows/`.

- most of the active runtime still lives under `ComicBook/comicbook/`, even though the CLI entry points, graph modules, image-workflow helper modules, and target-tree state/node wrappers now live under `workflows/`
- existing workflow commands and runtime paths are unchanged for operators
- workflow nodes and state ownership are still pending later TG2 and TG3 work
- only part of the temporary `comicbook` compatibility surface exists so far (`config`, `deps`, `repo_protection`, `fingerprint`, `db`, `execution`, `runtime_deps`, `state`, `nodes/*`, `input_file`, `router_prompts`, `metadata_prompts`, `router_llm`, `image_client`, `run`, `upload_run`, `graph`, and `upload_graph`, plus the package-root `upload_templates` re-export); test relocation and other cleanup work are still pending

That means the migration has updated project metadata and configuration guidance,
but it has not rolled the runtime itself over to the new package tree yet.

## Why this matters

The migration will eventually place multiple workflows under one package. Before that move can be safe, the repository needs one logging format that works the same way across workflows and shared infrastructure.

TG1 establishes that shared contract first so later migration steps can adopt it without introducing a second logging implementation.

## Current rollout status

- TG1: complete
- TG2: in progress (bootstrap + shared config/deps + repo-protection + fingerprint + db + execution + runtime-deps + CLI entry-point + workflow-graph + image-helper-module + state/node-wrapper slices complete)
- TG3-TG5: not started

## Related documents

- [Planning and execution guide](../../planning/repo-reorganization/index.md)
- [Developer notes](../../developer/repo-reorganization/index.md)
- [Logging standards](../../standards/logging-standards.md)
