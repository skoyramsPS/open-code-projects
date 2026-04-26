# Repository Reorganization

Developer notes for the phased migration from `ComicBook/comicbook/` to `workflows/pipelines/`.

## Current implementation status

- TG1: complete
- TG2: complete
- TG3-TG5: not started

TG1 established the shared logging foundation first so later package moves could reuse one tested logging implementation. TG2 then moved the target-tree project metadata, shared infrastructure modules, workflow entry points, workflow graph modules, image-workflow helper modules, explicit target-tree state/node bridge wrappers, the full current pytest tree into `workflows/tests/`, and the real workflow node modules into `workflows/` while preserving legacy import behavior through compatibility aliases. TG2 also completed the image-workflow doc-slug normalization, refreshed maintainer/tooling references, and closed with a green full target-tree pytest run.

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

### Bounded image-helper test relocation

- added `workflows/tests/image_prompt_gen/test_input_file_support.py`, `test_router_validation.py`, and `test_image_client.py` as target-root coverage for already-moved non-node image helper modules
- the relocated helper tests now import `pipelines.workflows.image_prompt_gen.input_file`, `pipelines.workflows.image_prompt_gen.run`, `pipelines.workflows.image_prompt_gen.prompts.router_prompts`, and `pipelines.workflows.image_prompt_gen.adapters.image_client` directly
- the old legacy helper-test files under `ComicBook/tests/` still remain for now because cleanup and deletion are deferred to later TG2 work

### Bounded template-upload test relocation

- added `workflows/tests/template_upload/support.py`, `test_graph_scenarios.py`, and `test_run_cli.py` as target-root coverage for already-moved template-upload graph and CLI/run behavior
- the relocated template-upload tests now import `pipelines.workflows.template_upload.graph` and `pipelines.workflows.template_upload.run` directly, while reusing target-tree shared deps/db/config helpers
- the old legacy template-upload regression files under `ComicBook/tests/` still remain for now because cleanup and deletion are deferred to later TG2 work

### Bounded image budget-guard test relocation

- added `workflows/tests/image_prompt_gen/test_budget_guard.py` as target-root coverage for already-moved image-workflow budget guard, dry-run redaction, and CLI budget-flag behavior
- the relocated budget-guard tests now import `pipelines.workflows.image_prompt_gen.graph` and `pipelines.workflows.image_prompt_gen.run` directly, while reusing target-tree shared config/deps/db helpers
- the old legacy `ComicBook/tests/test_budget_guard.py` regression file still remains for now because cleanup and deletion are deferred to later TG2 work

### Bounded shared config/state-contract test relocation

- added `workflows/tests/shared/test_config_and_compat_state.py` as target-root coverage for shared config loading and the temporary `comicbook.state` compatibility surface that still fronts the legacy mixed state module
- the relocated tests import `pipelines.shared.config` directly and validate the target-tree `comicbook.state` wrapper contract while TG3 state splitting is still pending
- the old legacy `ComicBook/tests/test_config.py` regression file still remains for now because cleanup and deletion are deferred to later TG2 work

### Bounded example-continuity coverage

- added `workflows/tests/image_prompt_gen/test_example_single_portrait.py` as target-root coverage for `workflows/examples/single_portrait_graph.py`
- the target-tree test now loads the moved example file by path, runs it with the target-root compatibility surface, and confirms the example still works from the new asset location
- the same test file also asserts that `pipelines/shared/` modules do not import workflow graph/run entry modules directly
- the old legacy `ComicBook/tests/test_example_single_portrait.py` regression file still remains for now because cleanup and deletion are deferred to later TG2 work

### Bounded fingerprint-regression expansion

- expanded `workflows/tests/shared/test_fingerprint.py` with additional target-root coverage for fingerprint hash drift and prompt/template ordering invariants
- the new target-tree cases mirror remaining non-node legacy fingerprint assertions while still avoiding node-owned `persist_template` relocation
- the old legacy `ComicBook/tests/test_fingerprint.py` regression file still remains for now because cleanup and deletion are deferred to later TG2 work

### Bounded node-wrapper continuity coverage

- added `workflows/tests/image_prompt_gen/test_node_ingest_summarize.py` as target-root coverage for the explicit `comicbook.nodes.ingest` and `comicbook.nodes.summarize` wrappers
- the new target-tree tests exercise still-legacy node implementations through the target-root compatibility layer rather than through the old package-root fallback
- this slice intentionally stays bounded to wrapper continuity for two nodes and does not start broader node-test relocation yet
- the old legacy `ComicBook/tests/test_node_ingest_summarize.py` regression file still remains for now because cleanup and deletion are deferred to later TG2 work

### Bounded image-node continuity expansion

- added `workflows/tests/image_prompt_gen/test_node_load_templates.py`, `test_node_cache_lookup.py`, and `test_node_router.py` as target-root coverage for the explicit `comicbook.nodes.load_templates`, `comicbook.nodes.cache_lookup`, and `comicbook.nodes.router` wrappers
- the new target-tree tests exercise those image node implementations through the target-root compatibility layer before and after the source-of-truth move into the `pipelines` package
- the matching legacy regression files under `ComicBook/tests/` still remain for now because cleanup and deletion are deferred to later TG2 work

### First actual image-node moves

- created `workflows/pipelines/workflows/image_prompt_gen/nodes/` and moved `load_templates.py`, `cache_lookup.py`, and `router.py` into that package as the new source-of-truth image nodes
- converted `ComicBook/comicbook/nodes/load_templates.py`, `cache_lookup.py`, and `router.py` into legacy compatibility aliases to the moved target-tree modules
- kept `workflows/comicbook/nodes/*.py` compatibility aliases working unchanged because they already resolve through the legacy module path, which now aliases to the moved target-tree module object
- updated `pipelines.workflows.image_prompt_gen.graph` to import the moved target-tree `load_templates`, `cache_lookup`, and `router` nodes directly while the remaining image nodes continue through compatibility aliases until later TG2 slices

### Bounded image generation-node continuity coverage

- added `workflows/tests/image_prompt_gen/test_node_generate_images_serial.py` as target-root coverage for the explicit `comicbook.nodes.generate_images_serial` wrapper
- the new target-tree tests exercise resume handling, non-retryable failure continuation, and rate-limit circuit-breaker behavior through the target-root compatibility layer before and after the source-of-truth move
- the matching legacy regression file under `ComicBook/tests/` still remains for now because cleanup and deletion are deferred to later TG2 work

### Second actual image-node move

- moved `generate_images_serial.py` into `workflows/pipelines/workflows/image_prompt_gen/nodes/` as another source-of-truth image node
- converted `ComicBook/comicbook/nodes/generate_images_serial.py` into a legacy compatibility alias to the moved target-tree module
- updated `pipelines.workflows.image_prompt_gen.graph` to import the moved target-tree `generate_images_serial` node directly
- expanded `workflows/tests/shared/test_compat_state_and_nodes.py` so it now proves the `comicbook.nodes.generate_images_serial` wrapper resolves to the moved target-tree module object

### Completed image-node move

- moved `ingest.py`, `persist_template.py`, and `summarize.py` into `workflows/pipelines/workflows/image_prompt_gen/nodes/`
- converted the matching `ComicBook/comicbook/nodes/*.py` files into legacy compatibility aliases to the moved target-tree modules
- updated `pipelines.workflows.image_prompt_gen.graph` so every image-workflow node now imports from the target-tree workflow package directly

### Completed template-upload node move

- created `workflows/pipelines/workflows/template_upload/nodes/` and moved all template-upload nodes into that package while intentionally keeping the `upload_*` filenames/functions for TG2 per the guide
- converted the matching `ComicBook/comicbook/nodes/upload_*.py` files into legacy compatibility aliases to the moved target-tree modules
- updated `pipelines.workflows.template_upload.graph` so every template-upload node now imports from the target-tree workflow package directly
- expanded `workflows/tests/shared/test_compat_state_and_nodes.py` so it now proves the target-tree `comicbook.nodes.upload_*` wrappers resolve to the moved target-tree module objects

### TG2 adjacent-asset move

- moved `ComicBook/examples/` to `workflows/examples/` with `git mv` so git history is preserved for the shared example assets
- moved `ComicBook/DoNotChange/` to `workflows/DoNotChange/` with `git mv` so the protected reference scripts now live under the target repository root
- updated `pipelines.shared.repo_protection`, the target-tree repo-protection tests, and the moved example continuity test to use the new asset locations
- kept `ComicBook/scripts/check_do_not_change.py` as the temporary legacy entry point, but updated docs and hook labeling so the protection surface now refers to `workflows/DoNotChange/`

### Bounded template-upload preflight node coverage

- added `workflows/tests/template_upload/test_node_preflight.py` as target-root coverage for the explicit `comicbook.nodes.upload_load_file`, `upload_parse_and_validate`, `upload_resume_filter`, and `upload_decide_write_mode` wrappers
- the new target-tree tests exercise still-legacy upload preflight node implementations through the target-root compatibility layer rather than through the old package-root fallback
- this slice intentionally stays bounded to the upload preflight node cluster and does not start later upload-node relocation such as persist/backfill yet
- the old legacy `ComicBook/tests/test_upload_load_file.py`, `test_upload_parse_and_validate.py`, `test_upload_resume_filter.py`, and `test_upload_decide_write_mode.py` files still remain for now because cleanup and deletion are deferred to later TG2 work

### Bounded template-upload backfill node coverage

- added `workflows/tests/template_upload/test_node_backfill_metadata.py` as target-root coverage for the explicit `comicbook.nodes.upload_backfill_metadata` wrapper
- the new target-tree tests exercise the still-legacy metadata-backfill node implementation through the target-root compatibility layer rather than through the old package-root fallback
- this slice intentionally stays bounded to the metadata-backfill node and does not start later upload persistence-node relocation yet
- the old legacy `ComicBook/tests/test_upload_backfill_metadata.py` file still remains for now because cleanup and deletion are deferred to later TG2 work

### Bounded template-upload persist node coverage

- added `workflows/tests/template_upload/test_node_persist.py` as target-root coverage for the explicit `comicbook.nodes.upload_persist` wrapper
- the new target-tree tests exercise the still-legacy persistence node implementation through the target-root compatibility layer rather than through the old package-root fallback
- this slice intentionally stays bounded to the persistence node and does not start delete cleanup or broader upload-node relocation beyond this wrapper-backed continuity layer
- the old legacy `ComicBook/tests/test_upload_persist.py` file still remains for now because cleanup and deletion are deferred to later TG2 work

### TG2 completed test relocation sweep

- removed the remaining duplicate legacy `ComicBook/tests/test_*.py` files after verifying the target-tree counterparts under `workflows/tests/`
- moved the last remaining unique legacy regression (`test_router_node.py`) into `workflows/tests/image_prompt_gen/test_router_node.py` and updated it to import the target-tree node module directly
- folded the remaining unique shared-config assertion (environment-overrides-dotenv) into `workflows/tests/shared/test_config_and_deps.py`
- deleted the legacy `ComicBook/tests/` directory after the duplicate-removal sweep and cleaned approved `__pycache__` artifacts created during verification

### TG2 doc-slug normalization

- renamed the image-workflow planning, business, and developer doc folders to the canonical lowercase slug `image-prompt-gen-workflow`
- updated cross-doc links in the top-level indexes, implementation-execution workflow docs, ADR references, related workflow plans, and the image-workflow implementation/handoff docs
- verified that the old mixed-case slug no longer appears anywhere in `docs/`, `AGENTS.md`, or `.opencode/`

### TG2 tooling-reference sweep

- updated `AGENTS.md` so it points new work at `workflows/pipelines/` and describes `ComicBook/comicbook/` only as a temporary compatibility-wrapper location
- updated `.opencode/agents/test-engineer.md` so it treats `workflows/tests/` as the canonical pytest tree and `ComicBook/tests/` as historical context only
- updated `.opencode/agents/langgraph-architect.md` so design output treats `ComicBook/comicbook/` as transitional compatibility surface, not the target ownership layout
- reviewed `opencode.json` and `.pre-commit-config.yaml`; no path rewrite was required there because the current entries are still valid during the shim window

## Verification

TG2 exit-gate verification now also includes the full target-tree suite from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q
```

Result: all scopes passed; the full suite finished at `165 passed`.

Focused verification for the migrated target-tree test scope now runs from `workflows/` while still reusing the existing locked dependency environment from `ComicBook/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/shared/test_runtime_deps.py tests/image_prompt_gen tests/template_upload/test_graph.py tests/template_upload/test_run.py
```

The broadened target-tree regression scope now also includes the relocated template-upload scenario/CLI tests via `tests/template_upload`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_compat_state_and_nodes.py tests/shared/test_runtime_deps.py tests/image_prompt_gen tests/template_upload
```

An even broader target-tree regression scope now also proves the relocated shared config/state-contract slice alongside the existing shared/workflow coverage:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared tests/image_prompt_gen tests/template_upload
```

Focused target-tree example continuity now also runs from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen/test_example_single_portrait.py
```

Focused target-tree fingerprint regression expansion now also runs from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_fingerprint.py
```

Focused target-tree node-wrapper continuity now also runs from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen/test_node_ingest_summarize.py
```

Focused target-tree template-upload preflight node continuity now also runs from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload/test_node_preflight.py
```

Focused target-tree template-upload backfill node continuity now also runs from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload/test_node_backfill_metadata.py
```

Focused target-tree template-upload persist node continuity now also runs from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/template_upload/test_node_persist.py
```

Representative legacy continuity for the moved helper, node, and graph surfaces was also checked from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_input_file_support.py tests/test_router_validation.py tests/test_image_client.py
```

And the matching image budget continuity check from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_budget_guard.py
```

And the matching shared config/state continuity check from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_config.py
```

And the matching legacy example continuity check from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_example_single_portrait.py
```

And the matching legacy fingerprint continuity check from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_fingerprint.py
```

And the matching legacy node-wrapper continuity check from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_node_ingest_summarize.py
```

And the matching legacy template-upload preflight continuity checks from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_upload_load_file.py tests/test_upload_parse_and_validate.py tests/test_upload_resume_filter.py tests/test_upload_decide_write_mode.py
```

And the matching legacy template-upload backfill continuity check from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_upload_backfill_metadata.py
```

And the matching legacy template-upload persist continuity check from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_upload_persist.py
```

And the matching template-upload continuity check from `ComicBook/`:

```bash
PYTHONPATH=. uv run --project "." --no-sync pytest -q tests/test_upload_graph.py tests/test_upload_run_cli.py
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

- start TG3 state splitting
- adopt node-level structured logging everywhere (TG4)
- remove the temporary compatibility layers (TG5)

Those changes remain sequenced behind TG2 and later TaskGroups in the implementation guide.

## Next expected slice

The next slice is TG3: split state ownership into `pipelines.shared.state`, `pipelines.workflows.image_prompt_gen.state`, and `pipelines.workflows.template_upload.state`, then rewire importers and boundary tests accordingly.

## Related documents

- [Planning and handoff](../../planning/repo-reorganization/index.md)
- [Business-facing status](../../business/repo-reorganization/index.md)
- [ADR-0002](../../planning/adr/ADR-0002-repo-reorganization.md)
