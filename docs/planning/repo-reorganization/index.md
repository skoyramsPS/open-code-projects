# Repository Reorganization

Planning material and completion record for the repository move from a flat single-package layout to a per-workflow layout under `workflows/pipelines/` with a shared logging standard.

## Documents

- [Reorganization plan](plan.md)
- [Implementation guide (current, v2)](implementation-v2.md) — authoritative; rewritten on 2026-04-25 with stricter standards (verified-baseline section, canonical `TG{N}-T{M}` task IDs, fully enumerated file lists, mandatory appendices, runnable exit criteria, and per-TaskGroup rollback notes).
- [Implementation guide (preserved, v1)](implementation.md) — historical; superseded by v2 but kept on disk for traceability of earlier execution.
- [Implementation handoff](implementation-handoff.md)

## Related

- [ADR-0002: Reorganize the repository into a multi-workflow `pipelines` package with a shared logging standard](../adr/ADR-0002-repo-reorganization.md)
- [Business status](../../business/repo-reorganization/index.md)
- [Developer notes](../../developer/repo-reorganization/index.md)
- [Repository structure standards](../../standards/repo-structure.md)
- [Logging standards](../../standards/logging-standards.md)

## Status

Implementation closeout is in progress.

- TG1 is complete: the shared logging foundation in `workflows/pipelines/shared/logging.py` is now covered by focused tests.
- TG2 has started with a bootstrap slice: `workflows/pyproject.toml` now defines the target-tree project metadata and `workflows/.env.example` now holds the shared environment template.
- TG2 has now started the shared-module move: `config.py`, `deps.py`, `repo_protection.py`, `fingerprint.py`, `db.py`, `execution.py`, and `runtime_deps.py` live under `workflows/pipelines/shared/`, and temporary `workflows/comicbook/` compatibility wrappers now exist for those modules.
- TG2 has now moved the workflow CLI entry points into `workflows/pipelines/workflows/image_prompt_gen/run.py` and `workflows/pipelines/workflows/template_upload/run.py`.
- Both target-tree and legacy `comicbook.run` / `comicbook.upload_run` paths now resolve through module-alias wrappers, which keeps monkeypatching and existing test behavior intact while the source of truth lives under `pipelines.workflows.*`.
- The moved CLI and library entry points now emit structured `log_event(...)` records directly for batch progress, single-run lifecycle events, import-run lifecycle events, and CLI error handling.
- TG2 has now moved the workflow graph modules into `workflows/pipelines/workflows/image_prompt_gen/graph.py` and `workflows/pipelines/workflows/template_upload/graph.py`.
- Both target-tree and legacy `comicbook.graph` / `comicbook.upload_graph` paths now resolve through module-alias wrappers, so the moved entry points execute through the target-tree graph modules while monkeypatch behavior stays intact.
- TG2 has now moved the image-workflow helper modules and pricing asset into `workflows/pipelines/workflows/image_prompt_gen/`, including `input_file.py`, `prompts/router_prompts.py`, `prompts/metadata_prompts.py`, `adapters/router_llm.py`, `adapters/image_client.py`, and `pricing.json`.
- Both target-tree and legacy `comicbook.input_file`, `comicbook.router_prompts`, `comicbook.metadata_prompts`, `comicbook.router_llm`, and `comicbook.image_client` paths now resolve through explicit compatibility aliases to the moved target-tree modules.
- TG2 now also provides explicit `workflows/comicbook/state.py` and `workflows/comicbook/nodes/` wrappers so the moved graph layer no longer depends on the old `ComicBook/comicbook` package-path fallback.
- TG2 has now begun bounded test relocation into `workflows/tests/`, starting with target-tree image graph scenario regressions under `workflows/tests/image_prompt_gen/test_graph_scenarios.py`.
- TG2 now also includes bounded target-tree relocation of the non-node image helper tests under `workflows/tests/image_prompt_gen/test_input_file_support.py`, `test_router_validation.py`, and `test_image_client.py`.
- TG2 now also includes bounded target-tree relocation of template-upload graph and CLI regression tests under `workflows/tests/template_upload/test_graph_scenarios.py` and `test_run_cli.py`.
- TG2 now also includes bounded target-tree relocation of the image-workflow budget and dry-run guard regressions under `workflows/tests/image_prompt_gen/test_budget_guard.py`.
- TG2 now also includes bounded target-tree relocation of shared config and legacy-state contract regressions under `workflows/tests/shared/test_config_and_compat_state.py`.
- TG2 now also includes bounded target-tree example-continuity coverage under `workflows/tests/image_prompt_gen/test_example_single_portrait.py`, proving the legacy single-portrait example still runs from the target root through the compatibility surface.
- TG2 now also includes bounded target-tree fingerprint regression expansion under `workflows/tests/shared/test_fingerprint.py`, covering additional hash-input and prompt-order invariants from the new root.
- TG2 now also includes bounded target-tree node-wrapper continuity coverage under `workflows/tests/image_prompt_gen/test_node_ingest_summarize.py`, proving the explicit `comicbook.nodes` wrapper surface works from the target root for the still-legacy ingest/summarize nodes.
- TG2 now also includes bounded target-tree node continuity coverage under `workflows/tests/image_prompt_gen/test_node_load_templates.py`, `test_node_cache_lookup.py`, and `test_node_router.py`.
- TG2 has now started the actual image-node move under `workflows/pipelines/workflows/image_prompt_gen/nodes/`: `load_templates.py`, `cache_lookup.py`, and `router.py` now live in the target tree, while both `ComicBook/comicbook/nodes/` and `workflows/comicbook/nodes/` preserve compatibility aliases.
- TG2 now also includes bounded target-tree node continuity coverage under `workflows/tests/image_prompt_gen/test_node_generate_images_serial.py`.
- TG2 has now extended the actual image-node move under `workflows/pipelines/workflows/image_prompt_gen/nodes/`: `generate_images_serial.py` now also lives in the target tree, and the image graph imports it directly while compatibility aliases continue to preserve legacy imports.
- TG2 has now completed the actual image-node move: `ingest.py`, `persist_template.py`, and `summarize.py` now also live under `workflows/pipelines/workflows/image_prompt_gen/nodes/`, so the image workflow graph imports all of its own target-tree nodes directly.
- TG2 now also includes bounded target-tree template-upload preflight node coverage under `workflows/tests/template_upload/test_node_preflight.py`, proving the explicit `comicbook.nodes.upload_*` wrapper surface works from the target root for the still-legacy upload preflight nodes.
- TG2 now also includes bounded target-tree template-upload backfill node coverage under `workflows/tests/template_upload/test_node_backfill_metadata.py`, proving the explicit `comicbook.nodes.upload_backfill_metadata` wrapper surface works from the target root for the still-legacy metadata-backfill node.
- TG2 now also includes bounded target-tree template-upload persist node coverage under `workflows/tests/template_upload/test_node_persist.py`, proving the explicit `comicbook.nodes.upload_persist` wrapper surface works from the target root for the still-legacy persistence node.
- TG2 has now completed the template-upload node move under `workflows/pipelines/workflows/template_upload/nodes/`: the preflight nodes (`upload_load_file.py`, `upload_parse_and_validate.py`, `upload_resume_filter.py`, `upload_decide_write_mode.py`) plus `upload_backfill_metadata.py`, `upload_persist.py`, and `upload_summarize.py` now live in the target tree while compatibility aliases preserve legacy imports.
- TG2 has now completed the adjacent-asset move: `workflows/examples/` and `workflows/DoNotChange/` are the live asset locations, and repo-protection references have been updated to match.
- TG2 has now completed the target-tree test relocation sweep: the remaining legacy `ComicBook/tests/` cases were either moved into `workflows/tests/` (including direct router-node coverage) or deleted after their target-tree counterparts were verified.
- TG2 has now completed the image-workflow doc-slug normalization: the planning, business, and developer folders all use `image-prompt-gen-workflow`, and the cross-doc links were updated to match.
- TG2 has now completed the tooling-reference sweep: stale agent and maintainer guidance that still implied `ComicBook/tests/` or legacy source-of-truth code paths was updated, while still-valid compatibility-wrapper references remain explicitly marked as transitional.
- TG2 has now completed the full target-tree suite gate: `tests/shared`, `tests/image_prompt_gen`, `tests/template_upload`, and the full `pytest -q` run all pass from `workflows/`.
- TG2 has now completed its documentation gate: `workflows/` is documented as the active project root, the `comicbook` shim is documented as transitional, non-node logging adoption is recorded, and the image-workflow doc slug is normalized across the triad.
- TG2 is complete.
- TG3 is now complete: state ownership is split across `pipelines.shared.state`, `pipelines.workflows.image_prompt_gen.state`, and `pipelines.workflows.template_upload.state`; workflow/runtime importers now reference the correct module; both compatibility `state.py` wrappers re-export the split symbols; and focused boundary coverage plus a full target-tree pytest run are green.
- TG4 is now complete: node-level lifecycle logging is wired through reusable decorators around every image-workflow node, every template-upload node, and the graph-local helper nodes (`runtime_gate`, `prepare_deferred_retry`), focused log-shape tests prove representative end-to-end runs emit parseable JSON records carrying `workflow`, `run_id`, `event`, and `node`, and the template-upload runtime now uses unprefixed node module/function names while compatibility wrappers preserve the legacy `upload_*` import surface.
- TG5 cleanup has landed: the `comicbook` compatibility shim was removed, package discovery was narrowed to `pipelines*`, shared metadata-backfill and Responses helpers were promoted into `pipelines.shared`, and tooling/docs were refreshed to the final layout.
- Final TG5 completion is still blocked on the guide-required pytest and CLI verification because the old locked `ComicBook` uv project was removed during cleanup and the local `workflows/` environment does not yet have pytest installed. Continuing requires explicit install/sync approval.
