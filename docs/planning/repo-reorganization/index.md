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
- The broader TG2 test-move, asset-move, and remaining compatibility-cleanup work are still pending.
