# ComicBook Image Prompt Workflow

Local Python workflow for turning a free-form prompt into one or more comic-style image generations with LangGraph, SQLite, and Azure OpenAI.

## What this package does

The shipped workflow currently supports:

- loading stored style templates from SQLite
- asking a router LLM for a structured generation plan
- optionally persisting a newly extracted template before prompt rendering
- building deterministic rendered prompts and prompt fingerprints
- reusing cached images when a matching fingerprint already exists
- generating uncached images serially with `n=1`
- writing run reports to `runs/<run_id>/report.md`
- writing structured summaries to `logs/<run_id>.summary.json`
- resuming partially completed runs with the same `--run-id`

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) for the documented local commands
- Azure OpenAI access for live workflow runs

## Configuration

Work from the `ComicBook/` directory.

1. Create a local `.env` from `.env.example`.
2. Fill in the required Azure values.
3. Leave optional paths and budget settings at their defaults unless you need to override them.

Required configuration values:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`
- `AZURE_OPENAI_IMAGE_DEPLOYMENT`

Optional workflow values:

- `COMICBOOK_DB_PATH`
- `COMICBOOK_IMAGE_OUTPUT_DIR`
- `COMICBOOK_RUNS_DIR`
- `COMICBOOK_LOGS_DIR`
- `COMICBOOK_ROUTER_MODEL_FALLBACK`
- `COMICBOOK_ROUTER_MODEL_ESCALATION`
- `COMICBOOK_DAILY_BUDGET_USD`
- `COMICBOOK_ROUTER_PROMPT_VERSION`
- `COMICBOOK_ENABLE_ROUTER_PREFLIGHT`

See `ComicBook/.env.example` for the current defaults.

## Run the mocked test suite

From `ComicBook/`:

```bash
uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q
```

Latest recorded result in TG8 validation work: `55 passed`.

## CLI usage

From `ComicBook/`:

```bash
uv run python -m comicbook.run "A four-panel comic where Lord Rama meets a wandering sage at dawn"
```

Supported flags:

- `--run-id <id>`: resume or rerun a specific workflow run
- `--dry-run`: stop after planning, cache lookup, and report generation
- `--force`: bypass cache-hit reuse for the current run
- `--panels <1-12>`: require an exact image count from the router
- `--budget-usd <amount>`: fail before image generation when estimated cost would exceed the run budget
- `--redact-prompts`: hash prompt text in generated reports and summaries

Example dry run:

```bash
uv run python -m comicbook.run \
  "A mythic sunrise duel in watercolor storybook style" \
  --dry-run \
  --panels 2 \
  --redact-prompts
```

Example resumable run:

```bash
uv run python -m comicbook.run \
  "A detective crow walking through a neon alley" \
  --run-id demo-resume-001
```

The CLI prints a small JSON payload with the `run_id` and terminal `run_status`.

## Library usage

```python
from comicbook.run import run_once

state = run_once(
    "A single heroic portrait with painterly gold lighting",
    dry_run=True,
    panels=1,
)

print(state["run_id"], state["run_status"])
```

## Output locations

- generated images: `image_output/<run_id>/`
- markdown run report: `runs/<run_id>/report.md`
- structured run summary: `logs/<run_id>.summary.json`
- SQLite database: `comicbook.sqlite` by default

## Operator notes

- image generation is intentionally serial and each request uses `n=1`
- rerunning the same rendered prompt without `--force` should produce cache hits instead of new image calls
- `--dry-run` still writes the markdown and JSON artifacts
- budget guards stop the workflow before any image API call when the estimated cost would exceed the configured limit
- the repository includes a protection check for `ComicBook/DoNotChange/`; do not edit those reference scripts

## Live smoke testing

Live Azure smoke validation is intentionally not part of the default mocked workflow test suite. Only run a live smoke when you explicitly intend to spend real Azure quota and have confirmed valid secrets are loaded.

The remaining TG8 closeout step is to record one approved live smoke invocation and its result in the implementation handoff once that opt-in is provided.
