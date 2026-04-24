# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG8 documentation-and-validation closeout slice in progress after TG7 completion
- Last updated: 2026-04-23

## What exists today

The repository now contains the reusable foundation for the image prompt generation workflow:

- environment-driven configuration loading with `.env` fallback
- validated state and schema contracts for router plans, prompts, image results, and run summaries
- a frozen dependency container that later workflow nodes will receive explicitly
- a local project layout for tests, examples, run artifacts, logs, and image outputs
- a local SQLite persistence layer with schema initialization, prompt/image/template storage, and daily operator rollups
- one-run-at-a-time protection for a shared workflow database file, including same-host stale-lock recovery when the recorded PID is no longer alive
- a versioned router prompt contract with strict JSON-schema-backed plan validation
- deterministic template catalog pre-filtering so large libraries send only the most relevant 15 template summaries to the router
- rationale leak redaction that protects against accidentally echoing the router system prompt into stored operator-facing explanations
- a live router call path that sends the constrained JSON payload to the Azure Responses API and validates the structured response before it enters workflow state
- one automatic repair retry when the router returns invalid JSON or invalid template references
- deterministic escalation from `gpt-5.4-mini` to `gpt-5.4` when the first valid plan explicitly requests a stronger router pass
- persistence of a router-extracted template before later prompt composition begins
- deterministic construction of final rendered prompts from stored template text plus subject text
- stable prompt fingerprints that change whenever the rendered text, size, quality, or image model changes
- persistence of prompt fingerprint rows before image generation starts
- cache classification that reuses previously generated images unless the operator explicitly forces regeneration
- a reusable single-image Azure client that always sends one prompt per request with `n=1`
- serial image execution that processes uncached prompts in router order and persists an image result row for each prompt outcome
- a complete end-to-end workflow graph that runs ingest, template loading, router planning, template persistence, cache lookup, runtime gating, serial generation, and summary finalization in one ordered execution path
- a CLI and library runtime surface that accepts either a direct prompt string or a JSON/CSV input file, plus run IDs, dry-run mode, forced regeneration, exact panel counts, per-run budgets, and prompt redaction
- a runtime guard that estimates remaining image cost, stops generation when a configured per-run or daily budget would be exceeded, and records the failure in the persisted run summary
- human-readable `runs/<run_id>/report.md` artifacts and structured `logs/<run_id>.summary.json` files for every summarized run, including dry runs and budget-blocked runs
- sample JSON and CSV prompt files under `ComicBook/examples/` that show the supported batch-input shapes
- an alternate `examples/single_portrait_graph.py` example that proves the reusable modules can support a different graph shape without depending on the main CLI or workflow-specific graph assembly

TG7 is now complete, the package now includes `ComicBook/README.md` for local usage guidance, and TG8 has started with a fresh full mocked validation run. The remaining work is the explicitly gated live Azure smoke step plus final readiness closeout.

## Current validation snapshot

- Full mocked regression command: `uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q`
- Latest mocked result: `70 passed`
- Acceptance checks now have documented mocked evidence for the CLI surface, serial generation, cache reuse, resume behavior, dry-run reporting, budget guards, router repair/escalation, reusable example graph, and read-only reference-file protection.
- One live smoke result is still pending because that step requires an explicit opt-in before real Azure traffic is allowed.

## Expected operator inputs

Operators can now provide:

- a free-form user prompt or an input file
- Azure OpenAI connection settings
- optional workflow controls such as dry-run, forced regeneration, exact panel count, per-run budget, prompt redaction, and resume identifiers

The supported operational setup is still preparing the environment variables documented in `ComicBook/.env.example`.

The workflow now automatically:

- send the full template catalog when there are 30 or fewer saved templates
- send a deterministic top-15 subset when the catalog is larger than 30
- preserve the full catalog in workflow state so later steps can still resolve selected templates exactly
- retry the same router model once when the first response fails schema or workflow validation
- escalate once to the stronger router model when the validated mini-model plan marks the request as needing escalation
- save a newly extracted template into the database before that template is used for prompt composition
- reuse the existing stored template row instead of creating a duplicate when the extracted template text already matches an existing template
- compute a stable fingerprint for every rendered prompt input tuple so later slices can decide whether the image request is already cached
- create prompt records before later generation begins so repeated runs reuse the same fingerprint history
- treat an already generated image for the same fingerprint as a cache hit by default
- keep duplicate prompts from the router from turning into duplicate generation work within the same run
- let `--force` bypass cache hits while still preserving prompt persistence for auditability and resume support
- retry one-image Azure generation requests on `408`, `429`, and `5xx` responses, up to three total attempts
- stop retrying immediately when Azure rejects a prompt with a content-filter response
- resume a partially completed run by skipping the API call when `image_output/<run_id>/<fingerprint>.png` already exists
- stop the remaining serial loop after two consecutive prompts fully exhaust retries on `429` and mark the rest as skipped for rate-limit protection
- normalize workflow input into a tracked run ID and start timestamp before the graph proceeds
- estimate remaining image cost before serial generation begins
- stop before image generation when `--budget-usd` or `COMICBOOK_DAILY_BUDGET_USD` would be exceeded
- stop after router planning and cache classification when `--dry-run` is enabled, while still writing the report artifacts
- pass `--panels N` through to the router as a hard exact-image-count constraint
- hash prompt text in reports and summaries when `--redact-prompts` is enabled
- fully validate JSON and CSV prompt files before the first run starts
- execute input-file records serially in file order, with one normal workflow run per record
- generate a per-record `run_id` before execution when a JSON record omits one
- finalize each completed graph run with persisted cache-hit, generated, failed, and skipped counters plus the terminal run status
- write a shareable markdown report and JSON summary for every summarized run

## Workflow outputs

The workflow now produces:

- generated images under `image_output/<run_id>/`
- human-readable run reports under `runs/<run_id>/report.md`
- structured summaries under `logs/<run_id>.summary.json`

## How to run it

From the `ComicBook/` directory, operators can now use the documented local README flow:

- `uv run python -m comicbook.run "<prompt>"` for a normal execution
- `uv run python -m comicbook.run --input-file examples/prompts.sample.json` to run a JSON batch serially
- `uv run python -m comicbook.run --input-file examples/prompts.sample.csv --dry-run` to inspect a CSV batch without generating images
- add `--dry-run` to inspect the router plan, cache classification, and report outputs without generating images
- add `--panels N` to require an exact image count
- add `--budget-usd <amount>` to stop before image generation when the estimated cost would exceed the chosen budget
- add `--run-id <id>` when intentionally resuming or repeating a known single run

The single-run CLI prints the final `run_id` and `run_status`, while input-file mode prints a batch summary JSON with status counts and the processed `run_ids`. Detailed operator-facing outputs are still written to the per-run report and summary locations listed above.

## Persistence and operator safety now in place

- Workflow data is stored in a local SQLite database file.
- Templates are append-only. Duplicate inserts with the same name and style text are ignored.
- If an extracted template is a duplicate of an existing stored template, the workflow reuses the existing canonical template row instead of storing a second copy.
- Prompt fingerprints are computed deterministically for cache and resume behavior.
- Prompt fingerprint rows are persisted before generation, even when the prompt is already cached.
- Only previously generated image rows count as cache hits; failed image rows stay eligible for retry in later runs.
- Generated image rows are written for successful generations, resumed same-run file hits, terminal failures, and rate-limit circuit-breaker skips.
- Only one active workflow run may hold the database lock at a time.
- If a previous run died on the same host and its PID is no longer alive, the stale lock can be recovered automatically.
- Daily run rollups are available from the database for cache-hit and estimated-cost reporting.
- Completed graph runs release the SQLite lock by finalizing the `runs` row with the terminal status and counters.
- Budget-blocked runs fail before any image API call and still emit the same summary artifacts as successful runs.
- Dry runs stop before any image API call while still writing the operator-facing report and JSON summary.

## Guardrails and limitations

- Secrets are loaded from environment variables first, then `.env`.
- The workflow package does not modify the read-only reference scripts under `ComicBook/DoNotChange/`, and the repository now includes a commit-time protection check that rejects edits to those files.
- The graph orchestration, CLI entry point, dry-run path, budget guards, and report artifacts are now implemented.
- Input-file mode is intentionally a serial wrapper around the existing single-prompt workflow; it does not create a shared batch report file or a batch database object.
- The lock policy is intentionally conservative: one active run per SQLite file.
- The package layout is intentionally reusable so later workflows can share the same contracts.
- The repository now includes one alternate portrait-only example graph to demonstrate that the shared modules are not locked to a single orchestration entry point.
- Large template catalogs are filtered lexically only in v1; the workflow does not use semantic retrieval.
- `--run-id` cannot be combined with `--input-file`; resumable batch behavior depends on stable per-record `run_id` values instead.
- A live Azure smoke run is not executed automatically; it remains a deliberate, operator-approved validation step outside the default mocked test suite.

## Plain-language troubleshooting

If setup fails at this stage, the most likely causes are:

- missing Azure configuration, which is reported explicitly by the config loader
- a currently active run already holding the database lock for the chosen SQLite file
- a router response that references template IDs outside the allowed subset, which is rejected by the validation layer
- a router response that fails validation twice, which stops the router stage after the single allowed repair attempt
- a request that the mini router marks as ambiguous enough to escalate, which triggers one additional router call on the stronger model before later steps continue
- an input file that fails shape validation before any work starts, which is expected protection against malformed JSON, malformed CSV, blank prompts, duplicate `run_id` values, or unsupported fields and columns
- an extracted template that matches an existing stored template, which is treated as a safe deduplication hit rather than a hard failure
- a prompt that was expected to be cached but is still queued for generation, which can happen intentionally when `--force` is enabled or when the only prior image rows were failures
- an image prompt that Azure content filters, which records a per-image failure and lets the remaining serial work continue
- repeated `429` responses from Azure, which trigger a stop after two consecutive prompts fully exhaust their retries so the run does not keep hammering the endpoint
- a resume run that should have reused a finished same-run file, which inserts a generated image row from the existing file and avoids re-calling Azure for that fingerprint
- a dry run that wrote a report but no images, which is expected behavior when `--dry-run` is enabled
- a run that stops before image generation because the configured per-run or daily budget would be exceeded
- an input-file batch that returns a non-zero exit code because one or more records finished `partial` or `failed`, even though later validated records still continued to run
- a commit attempt that fails immediately because a file under `ComicBook/DoNotChange/` was edited, which is expected repository protection behavior rather than a workflow runtime failure

If the lock belongs to a dead process on the same machine, the runtime can recover it automatically through the persistence layer added in TG2.
