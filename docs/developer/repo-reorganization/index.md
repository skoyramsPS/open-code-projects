# Repository Reorganization

Developer notes for the phased migration from `ComicBook/comicbook/` to `workflows/pipelines/`.

## Current implementation status

- TG1: complete
- TG2: in progress (bootstrap + shared config/deps + repo-protection + fingerprint + db + execution + runtime-deps + CLI entry-point + workflow-graph + image-helper-module + state/node-wrapper + bounded image-test-relocation slices complete)
- TG3-TG5: not started

TG1 established the shared logging foundation first so later package moves could reuse one tested logging implementation. TG2 then moved the target-tree project metadata, shared infrastructure modules, workflow entry points, workflow graph modules, image-workflow helper modules, explicit target-tree state/node bridge wrappers, and now the first bounded batch of relocated image-workflow tests into `workflows/` while preserving legacy import behavior through compatibility aliases.

## TG1 deliverables

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

## TG2 slices completed so far

### Bootstrap

- added `workflows/pyproject.toml` so the target tree now carries package discovery and pytest configuration
- moved the shared environment template to `workflows/.env.example`
- updated setup-facing documentation and READMEs to point at the new environment-template path

### Shared modules

- moved `config.py`, `deps.py`, `repo_protection.py`, `fingerprint.py`, `db.py`, `execution.py`, and `runtime_deps.py` into `workflows/pipelines/shared/`
- added matching `workflows/comicbook/*.py` target-tree compatibility wrappers for those shared modules
- converted the matching `ComicBook/comicbook/*.py` shared modules into thin legacy wrappers

### Workflow entry points

- moved the image workflow entry point into `workflows/pipelines/workflows/image_prompt_gen/run.py`
- moved the template-upload entry point into `workflows/pipelines/workflows/template_upload/run.py`
- added `workflows/comicbook/run.py` and `workflows/comicbook/upload_run.py` as target-tree compatibility aliases
- converted `ComicBook/comicbook/run.py` and `ComicBook/comicbook/upload_run.py` into legacy compatibility aliases
- adopted `log_event(...)` for batch progress, single-run lifecycle, import-run lifecycle, and CLI error handling in the moved entry points

### Workflow graph modules

- moved the image workflow graph module into `workflows/pipelines/workflows/image_prompt_gen/graph.py`
- moved the template-upload workflow graph module into `workflows/pipelines/workflows/template_upload/graph.py`
- added `workflows/comicbook/graph.py` and `workflows/comicbook/upload_graph.py` as target-tree compatibility aliases
- converted `ComicBook/comicbook/graph.py` and `ComicBook/comicbook/upload_graph.py` into legacy compatibility aliases

### Image helper modules and pricing asset

- moved `input_file.py` into `workflows/pipelines/workflows/image_prompt_gen/input_file.py`
- moved `router_prompts.py` and `metadata_prompts.py` into `workflows/pipelines/workflows/image_prompt_gen/prompts/`
- moved `router_llm.py` and `image_client.py` into `workflows/pipelines/workflows/image_prompt_gen/adapters/`
- moved `pricing.json` into `workflows/pipelines/workflows/image_prompt_gen/pricing.json`
- added `workflows/comicbook/input_file.py`, `router_prompts.py`, `metadata_prompts.py`, `router_llm.py`, and `image_client.py` as target-tree compatibility aliases to those moved modules
- converted `ComicBook/comicbook/input_file.py`, `router_prompts.py`, `metadata_prompts.py`, `router_llm.py`, and `image_client.py` into legacy compatibility aliases so existing importers and monkeypatch-based tests now point at the moved source-of-truth modules
- switched `pipelines.workflows.image_prompt_gen.run` to import its input-file helpers directly from `pipelines.workflows.image_prompt_gen.input_file`
- ensured `pipelines.shared.runtime_deps._default_pricing_path()` now resolves the target-tree pricing asset first while retaining the legacy pricing path only as a temporary fallback guard

### Explicit target-tree state and node bridge wrappers

- added `workflows/comicbook/state.py` as an explicit target-tree compatibility wrapper for the still-legacy combined state module
- added `workflows/comicbook/nodes/` with explicit wrapper modules for the legacy nodes used by the moved graph layer
- removed the old `workflows/comicbook/__init__.py` package-path fallback to `ComicBook/comicbook/`
- proved the moved graph layer can now import `comicbook.state` and `comicbook.nodes.*` from the new root without depending on implicit package-path fallback

### Bounded image-workflow test relocation

- added `workflows/tests/image_prompt_gen/test_graph_scenarios.py` as the first bounded relocation of legacy image-workflow graph scenario coverage into the target tree
- added `workflows/tests/image_prompt_gen/support.py` so the relocated tests can share target-tree fixtures and fake transports without depending on the legacy test directory
- the relocated graph scenario tests now import `pipelines.shared.*` helpers and `pipelines.workflows.image_prompt_gen.graph` directly from the target root
- the old `ComicBook/tests/test_graph_*.py` files still remain for now because TG2 test cleanup and legacy-path removal are separate follow-up work

## Verification

Focused verification for the migrated target-tree test scope now runs from `workflows/` while still reusing the existing locked dependency environment from `ComicBook/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/shared/test_runtime_deps.py tests/image_prompt_gen tests/template_upload/test_graph.py tests/template_upload/test_run.py
```

Representative legacy continuity for the moved helper, node, and graph surfaces was also checked from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_graph_happy.py tests/test_graph_cache_hit.py tests/test_graph_resume.py tests/test_graph_new_template.py
```

Additional direct alias validation from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync python - <<'PY'
import comicbook
import comicbook.state as wrapped_state_module
import comicbook.nodes.ingest as wrapped_ingest_module
import comicbook.nodes.upload_load_file as wrapped_upload_load_file_module
from ComicBook.comicbook import state as legacy_state_module
from ComicBook.comicbook.nodes import ingest as legacy_ingest_module
from ComicBook.comicbook.nodes import upload_load_file as legacy_upload_load_file_module
print(all(not path.endswith('ComicBook/comicbook') for path in comicbook.__path__))
print(wrapped_state_module is legacy_state_module)
print(wrapped_ingest_module is legacy_ingest_module)
print(wrapped_upload_load_file_module is legacy_upload_load_file_module)
PY
```

The `pythonpath = ["."]` pytest setting in `workflows/pyproject.toml` keeps the target package importable from the new root without extra shell setup. This keeps the slices install-free while proving that `workflows/pyproject.toml` can now drive focused target-tree pytest scopes.

## Important boundaries

The completed TG1 + TG2 work does **not** yet:

- move runtime modules out of `ComicBook/comicbook/`
- move most workflow-owned modules such as node implementations and state ownership out of `ComicBook/comicbook/`
- start TG3 state splitting
- move the main legacy test suite out of `ComicBook/tests/` beyond the first bounded image-graph relocation
- finish the non-code asset moves and path-sensitive cleanup under TG2

Those changes remain sequenced behind TG2 and later TaskGroups in the implementation guide.

## Next expected slice

The next TG2 slice should continue bounded test relocation with the remaining non-node image-workflow helper regressions, most likely moving the input-file, router-validation, and image-client tests from `ComicBook/tests/` into `workflows/tests/image_prompt_gen/` while keeping node-owned tests deferred until their runtime ownership is cleaner.

## Related documents

- [Planning and handoff](../../planning/repo-reorganization/index.md)
- [Business-facing status](../../business/repo-reorganization/index.md)
- [ADR-0002](../../planning/adr/ADR-0002-repo-reorganization.md)
