# Image Prompt Generation Workflow

## Status

- Workflow delivery status: implemented
- Repository layout status: fully migrated to `workflows/pipelines/`
- Canonical runtime package: `pipelines.workflows.image_prompt_gen`

## Runtime surface

- CLI entry point: `python -m pipelines.workflows.image_prompt_gen.run`
- graph assembly: `pipelines.workflows.image_prompt_gen.graph`
- state contract: `pipelines.workflows.image_prompt_gen.state`
- image-workflow nodes: `pipelines.workflows.image_prompt_gen.nodes.*`

Shared dependencies used by this workflow now live under `pipelines.shared.*`, including:

- `config`, `deps`, `db`, `execution`, `fingerprint`, `logging`, and `state`
- `responses` for structured Responses API calls
- `repo_protection` for the protected-reference-file hook

## Module boundaries

- `input_file.py` handles JSON/CSV prompt-file parsing and validation
- `prompts/router_prompts.py` owns the router system prompt and router response schema
- `adapters/router_llm.py` owns router-plan request/repair/escalation behavior
- `adapters/image_client.py` owns one-image Azure generation behavior
- `nodes/ingest.py` normalizes initial state
- `nodes/load_templates.py` loads the template catalog and router-visible subset
- `nodes/router.py` executes the router call path and accumulates usage
- `nodes/persist_template.py` stores router-extracted templates before prompt composition
- `nodes/cache_lookup.py` materializes rendered prompts and classifies cache hits
- `nodes/generate_images_serial.py` performs serial generation and resume-aware persistence
- `nodes/summarize.py` writes reports and finalizes the persisted run summary

## State contract highlights

Primary workflow-owned models live in `pipelines.workflows.image_prompt_gen.state`.

Shared base types such as `WorkflowError`, `UsageTotals`, and `RunSummary` live in `pipelines.shared.state`.

## Commands

Run from `workflows/`.

```bash
uv run --project "." --no-sync python -m pipelines.workflows.image_prompt_gen.run --help
uv run --project "." --no-sync pytest -c pyproject.toml -q tests/image_prompt_gen
```

## Testing notes

- unit and integration-style workflow tests live under `workflows/tests/image_prompt_gen/`
- shared helper tests live under `workflows/tests/shared/`
- logging output is asserted only in dedicated logging tests

## Maintenance notes

- do not reintroduce `comicbook.*` imports
- keep node logging on `log_node_event(...)`
- keep non-node logging on `get_logger(__name__)` plus `log_event(...)`
- promote any workflow-local helper into `pipelines.shared/` when a second workflow imports it

For operator-facing usage, see `docs/business/image-prompt-gen-workflow/index.md`.
