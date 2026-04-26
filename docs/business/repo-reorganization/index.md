# Repository Reorganization

Plain-language status and operator-facing notes for the repository move into the `workflows/pipelines/` layout.

## What changed so far

Additional migration slices have landed so far.

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
- the legacy `ComicBook/scripts/check_do_not_change.py` script path still works, and it now protects `workflows/DoNotChange`

### TG2 adjacent-asset move

- the shared example assets now live under `workflows/examples/`
- the read-only reference scripts now live under `workflows/DoNotChange/`
- operator-facing example and protection paths now point at the new `workflows/` root while the legacy script entry point continues to work during the shim window

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

### TG2 bounded image-test relocation move

- test relocation into `workflows/tests/` has now started with image-workflow graph scenario regressions under `workflows/tests/image_prompt_gen/test_graph_scenarios.py`
- those target-tree tests now exercise the moved `pipelines.workflows.image_prompt_gen.graph` module directly from the new project root
- the old legacy test files still remain for now, so this slice improves target-root coverage without changing operator behavior or removing fallback paths yet

### TG2 bounded image-helper test relocation move

- target-tree relocation now also covers the already-moved non-node image helper modules: input-file parsing, router validation, and the image client adapter
- the new tests live under `workflows/tests/image_prompt_gen/` and run from the target root against `pipelines.workflows.image_prompt_gen.*`
- the old legacy helper-test files still remain for now, so this slice improves migration coverage without yet removing the legacy test entry points

### TG2 bounded template-upload test relocation move

- target-tree relocation now also covers the already-moved template-upload graph and CLI/run layers under `workflows/tests/template_upload/`
- the new tests exercise the moved `pipelines.workflows.template_upload.graph` and `pipelines.workflows.template_upload.run` modules directly from the target root
- the old legacy template-upload regression files still remain for now, so this slice improves migration coverage without yet removing legacy test entry points

### TG2 bounded image budget-guard test relocation move

- target-tree relocation now also covers the already-moved image-workflow budget and dry-run guard regressions under `workflows/tests/image_prompt_gen/test_budget_guard.py`
- the new tests exercise the moved `pipelines.workflows.image_prompt_gen.graph` and `pipelines.workflows.image_prompt_gen.run` modules directly from the target root
- the old legacy `ComicBook/tests/test_budget_guard.py` regression file still remains for now, so this slice improves migration coverage without yet removing the legacy test entry point

### TG2 bounded shared config/state-contract test relocation move

- target-tree relocation now also covers shared config loading plus the temporary legacy-state contract surface under `workflows/tests/shared/test_config_and_compat_state.py`
- the new tests exercise `pipelines.shared.config` directly and confirm that the target-tree `comicbook.state` wrapper still exposes the legacy mixed state contract while TG3 is pending
- the old legacy `ComicBook/tests/test_config.py` regression file still remains for now, so this slice improves migration coverage without yet removing the legacy test entry point

### TG2 bounded example-continuity test move

- target-tree coverage now also proves that the legacy single-portrait example still runs from the `workflows/` root through the temporary compatibility layer
- the new tests live under `workflows/tests/image_prompt_gen/test_example_single_portrait.py` and also assert that `pipelines/shared/` does not import workflow entry modules directly
- the old legacy `ComicBook/tests/test_example_single_portrait.py` regression file still remains for now, so this slice improves migration confidence without yet removing the legacy test entry point

### TG2 bounded fingerprint-regression expansion move

- target-tree shared coverage now also includes additional fingerprint invariants under `workflows/tests/shared/test_fingerprint.py`
- the expanded tests prove fingerprint hashes change when any render input changes and that rendered-prompt materialization preserves prompt/template ordering from the target root
- the old legacy `ComicBook/tests/test_fingerprint.py` regression file still remains for now, so this slice improves migration confidence without yet removing the legacy test entry point

### TG2 bounded node-wrapper continuity move

- target-tree coverage now also proves the explicit `comicbook.nodes` wrapper surface works from `workflows/` for the still-legacy image ingest/summarize nodes
- the new tests live under `workflows/tests/image_prompt_gen/test_node_ingest_summarize.py` and verify runtime-default ingestion plus redacted-summary artifact generation through the wrapper layer
- the old legacy `ComicBook/tests/test_node_ingest_summarize.py` regression file still remains for now, so this slice improves migration confidence without yet removing the legacy test entry point

### TG2 bounded image-node continuity expansion

- target-tree coverage now also proves the explicit `comicbook.nodes` wrapper surface works from `workflows/` for the image `load_templates`, `cache_lookup`, and `router` nodes
- the new tests live under `workflows/tests/image_prompt_gen/test_node_load_templates.py`, `test_node_cache_lookup.py`, and `test_node_router.py`
- the matching legacy regression files still remain for now, so these slices improve migration confidence without yet removing the legacy test entry points

### TG2 first actual image-node moves

- the real implementations for `load_templates`, `cache_lookup`, and `router` now live under `workflows/pipelines/workflows/image_prompt_gen/nodes/`
- both `ComicBook/comicbook/nodes/` and `workflows/comicbook/nodes/` continue to expose compatibility aliases, so operator-facing commands and legacy imports are unchanged
- the moved image graph now imports those target-tree node modules directly while the remaining image and upload nodes continue through the compatibility layer

### TG2 bounded image generation-node continuity move

- target-tree coverage now also proves the explicit `comicbook.nodes.generate_images_serial` wrapper surface works from `workflows/`
- the new tests live under `workflows/tests/image_prompt_gen/test_node_generate_images_serial.py`
- the matching legacy regression file still remains for now, so this slice improves migration confidence without yet removing the legacy test entry point

### TG2 second actual image-node move

- the real implementation for `generate_images_serial` now also lives under `workflows/pipelines/workflows/image_prompt_gen/nodes/`
- both `ComicBook/comicbook/nodes/` and `workflows/comicbook/nodes/` still expose compatibility aliases, so operator-facing behavior remains unchanged
- the moved image graph now imports `generate_images_serial` from the target-tree workflow package directly, further shrinking the still-legacy image runtime surface

### TG2 completed image-node move

- the remaining image nodes `ingest`, `persist_template`, and `summarize` now also live under `workflows/pipelines/workflows/image_prompt_gen/nodes/`
- both compatibility layers still preserve legacy imports, so operator-facing commands remain unchanged
- the image workflow graph now imports its full node set from the target-tree workflow package directly

### TG2 bounded template-upload preflight node move

- target-tree coverage now also proves the explicit `comicbook.nodes.upload_*` wrapper surface works from `workflows/` for the still-legacy upload preflight nodes
- the new tests live under `workflows/tests/template_upload/test_node_preflight.py` and verify file loading, parse/validate, resume filtering, and write-mode decisions through the wrapper layer
- the old legacy upload preflight regression files still remain for now, so this slice improves migration confidence without yet removing the legacy test entry points

### TG2 bounded template-upload backfill node move

- target-tree coverage now also proves the explicit `comicbook.nodes.upload_backfill_metadata` wrapper surface works from `workflows/` for the still-legacy metadata-backfill node
- the new tests live under `workflows/tests/template_upload/test_node_backfill_metadata.py` and verify successful backfill, retry-on-invalid-response, disabled-backfill handling, budget short-circuiting, and repeated transport-failure short-circuit behavior through the wrapper layer
- the old legacy `ComicBook/tests/test_upload_backfill_metadata.py` regression file still remains for now, so this slice improves migration confidence without yet removing the legacy test entry point

### TG2 bounded template-upload persist node move

- target-tree coverage now also proves the explicit `comicbook.nodes.upload_persist` wrapper surface works from `workflows/` for the still-legacy persistence node
- the new tests live under `workflows/tests/template_upload/test_node_persist.py` and verify inserted, updated, skipped-duplicate, failed-validation, and unresolved-supersedes persistence outcomes through the wrapper layer
- the old legacy `ComicBook/tests/test_upload_persist.py` regression file still remains for now, so this slice improves migration confidence without yet removing the legacy test entry point

### TG2 completed template-upload node move

- the preflight upload nodes plus `upload_backfill_metadata`, `upload_persist`, and `upload_summarize` now all live under `workflows/pipelines/workflows/template_upload/nodes/`
- both `ComicBook/comicbook/nodes/` and `workflows/comicbook/nodes/` still expose compatibility aliases, so operator-facing commands remain unchanged
- the template-upload graph now imports its full node set from the target-tree workflow package directly

### TG2 completed test relocation sweep

- the canonical pytest tree now lives entirely under `workflows/tests/`
- the final remaining legacy test-only coverage was moved into the target tree, including direct router-node coverage under `workflows/tests/image_prompt_gen/test_router_node.py`
- the duplicate legacy `ComicBook/tests/` regression files were removed after their target-tree counterparts were verified, so operator guidance no longer relies on the old test root

### TG2 doc-slug normalization

- the image prompt workflow docs now use the same lowercase slug under planning, business, and developer views: `image-prompt-gen-workflow`
- cross-document links, quick links, ADR references, and implementation-execution examples now point at the normalized slug
- this is a documentation-path cleanup only; it does not change operator commands or workflow behavior

### TG2 tooling-reference sweep

- maintainer-facing agent guidance no longer points engineers at the removed `ComicBook/tests/` tree as if it were still active
- repository guidance now treats `ComicBook/comicbook/` as a legacy compatibility-wrapper location, not the place for new source-of-truth work
- operator-facing behavior is unchanged; this slice tightened internal instructions only

## What has not changed yet

TG2 has completed the runtime-root move, but the migration is not finished overall.

- existing workflow commands and runtime behavior remain unchanged for operators because the compatibility layer still preserves legacy imports during the shim window
- workflow state ownership is still pending TG3 work
- the temporary `comicbook` compatibility surface still exists so older imports and scripts keep working while later TaskGroups land
- final shim removal and cleanup remain deferred to TG5

## Why this matters

The migration will eventually place multiple workflows under one package. Before that move can be safe, the repository needs one logging format that works the same way across workflows and shared infrastructure.

TG1 establishes that shared contract first so later migration steps can adopt it without introducing a second logging implementation.

## Current rollout status

- TG1: complete
- TG2: complete
- TG3-TG5: not started

## Related documents

- [Planning and execution guide](../../planning/repo-reorganization/index.md)
- [Developer notes](../../developer/repo-reorganization/index.md)
- [Logging standards](../../standards/logging-standards.md)
