# Repository Structure Standards

## OpenCode layout

Use these locations consistently:

- `AGENTS.md` at the repo root
- `opencode.json` at the repo root
- `.opencode/agents/` for project subagents
- `.opencode/commands/` for reusable commands
- `.opencode/skills/` for project-local skills
- `.opencode/tools/` only when built-in tools are insufficient

## Top-level repository layout

```
.
├── AGENTS.md
├── opencode.json
├── .opencode/
├── docs/
└── workflows/
    └── pipelines/        # the importable Python package
```

`workflows/` is the home for all Python workflow code. The package directory inside it is named `pipelines`, and that is the importable Python package. Subdirectories under `workflows/` other than `pipelines/` are reserved for non-Python workflow assets (Docker, infra, examples that must stay outside the package).

## Documentation layout

All durable docs live under `docs/`.

- `docs/planning/`
- `docs/business/`
- `docs/developer/`
- `docs/standards/`

Use the same workflow slug across all three documentation trees. Slugs are lowercase, hyphen-separated, and end with `-workflow`. Example:

- `docs/planning/image-prompt-gen-workflow/index.md`
- `docs/business/image-prompt-gen-workflow/index.md`
- `docs/developer/image-prompt-gen-workflow/index.md`

The mapping between Python workflow modules (snake_case) and doc slugs (hyphenated) is one-to-one and is recorded in this file:

| Python module under `pipelines.workflows.` | Doc slug under `docs/{planning,business,developer}/` |
| --- | --- |
| `image_prompt_gen` | `image-prompt-gen-workflow` |
| `template_upload` | `template-upload-workflow` |

When a new workflow is added, update this table in the same change that creates the workflow module.

## Python package layout

The `pipelines` package is organized so every workflow-specific concept lives next to its workflow, and every cross-workflow concept lives in `shared/`.

```
workflows/pipelines/
├── __init__.py
├── shared/
│   ├── __init__.py
│   ├── config.py             # AppConfig + load_config
│   ├── deps.py               # Deps dataclass
│   ├── runtime_deps.py       # build_runtime_deps, resolve_runtime_deps
│   ├── execution.py          # bind_node, run_graph_with_lock
│   ├── db.py                 # SQLite adapter
│   ├── fingerprint.py        # cross-workflow fingerprint helpers
│   ├── responses.py          # shared Responses API transport helpers
│   ├── metadata_backfill.py  # shared metadata-backfill prompt/schema helpers
│   ├── repo_protection.py
│   ├── logging.py            # see docs/standards/logging-standards.md
│   └── state.py              # WorkflowError, UsageTotals, RunSummary, common literals
└── workflows/
    ├── __init__.py
    ├── image_prompt_gen/
    │   ├── __init__.py
    │   ├── graph.py
    │   ├── run.py
    │   ├── state.py          # RunState + image-prompt-only models
    │   ├── pricing.json
    │   ├── prompts/
    │   │   └── router_prompts.py
    │   ├── adapters/
    │   │   ├── image_client.py
    │   │   └── router_llm.py
    │   └── nodes/
    │       ├── ingest.py
    │       ├── load_templates.py
    │       ├── router.py
    │       ├── persist_template.py
    │       ├── cache_lookup.py
    │       ├── generate_images_serial.py
    │       └── summarize.py
    └── template_upload/
        ├── __init__.py
        ├── graph.py
        ├── run.py
        ├── state.py          # ImportRunState + upload-only models
        └── nodes/
            ├── load_file.py
            ├── parse_and_validate.py
            ├── resume_filter.py
            ├── backfill_metadata.py
            ├── decide_write_mode.py
            ├── persist.py
            └── summarize.py
```

Key rules:

- workflow-specific nodes live under `pipelines/workflows/<workflow>/nodes/` — drop the legacy `upload_` prefix in module and function names since the directory already establishes scope
- a node that becomes useful in another workflow is promoted to `pipelines/shared/nodes/` (created on first need) and imported by both
- adapters and prompt files always live in the workflow they were originally written for; promote them to `shared/` only when a second workflow imports them
- `shared/state.py` holds only types that are referenced by code in two or more workflows; workflow-specific Pydantic models stay in the workflow's `state.py`
- workflow `state.py` files import their shared base types from `pipelines.shared.state` and add their own state TypedDict on top

## Tests

Tests stay outside the package, mirroring the package tree:

```
workflows/tests/
├── shared/
├── image_prompt_gen/
└── template_upload/
```

Within each subdirectory, file names follow `test_<thing>.py`. Cross-workflow integration tests live under `workflows/tests/integration/`.

## Naming

- Python workflow module names use `snake_case`
- doc slugs use `lowercase-hyphenated` and append `-workflow`
- skill names stay lowercase with hyphens
- node module names describe behavior, not workflow membership (the directory establishes that)
- shared modules use unprefixed names (`db.py`, not `comicbook_db.py`)
