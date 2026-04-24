# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG5 complete, adding serial image execution on top of router planning and cache preparation
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

This slice still does **not** execute the full workflow end to end, but it now establishes the router-planning stage, the full cache-preparation stage, and the serial image-execution stage that later graph wiring and reporting logic will rely on.

## Expected operator inputs

When later slices are added, operators will provide:

- a free-form user prompt
- Azure OpenAI connection settings
- optional workflow controls such as dry-run, panel count, budget, and resume identifiers

For now, the only supported operational setup is preparing the environment variables documented in `ComicBook/.env.example`.

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

## Expected outputs later in the workflow

The completed workflow is planned to produce:

- generated images under `image_output/<run_id>/`
- human-readable run reports under `runs/<run_id>/report.md`
- structured summaries under `logs/<run_id>.summary.json`

Those runtime artifacts are not produced yet in the current implementation slice.

## Persistence and operator safety now in place

- Workflow data is stored in a local SQLite database file.
- Templates are append-only. Duplicate inserts with the same name and style text are ignored.
- If an extracted template is a duplicate of an existing stored template, the workflow reuses the existing canonical template row instead of storing a second copy.
- Prompt fingerprints can now be computed deterministically for later cache and resume behavior.
- Prompt fingerprint rows are now persisted before generation, even when the prompt is already cached.
- Only previously generated image rows count as cache hits; failed image rows stay eligible for retry in later slices.
- Generated image rows are now written for successful generations, resumed same-run file hits, terminal failures, and rate-limit circuit-breaker skips.
- Only one active workflow run may hold the database lock at a time.
- If a previous run died on the same host and its PID is no longer alive, the stale lock can be recovered automatically.
- Daily run rollups are now available from the database for cache-hit and estimated-cost reporting.

## Guardrails and limitations

- Secrets are loaded from environment variables first, then `.env`.
- The workflow package does not modify the read-only reference scripts under `ComicBook/DoNotChange/`.
- The router stage, cache-preparation helpers, and serial image execution are implemented, but later slices still need graph wiring, CLI entry points, budget enforcement, and reporting artifacts.
- The lock policy is intentionally conservative: one active run per SQLite file.
- The package layout is intentionally reusable so later workflows can share the same contracts.
- Large template catalogs are filtered lexically only in v1; the workflow does not yet use semantic retrieval.

## Plain-language troubleshooting

If setup fails at this stage, the most likely causes are:

- missing Azure configuration, which is reported explicitly by the config loader
- a currently active run already holding the database lock for the chosen SQLite file
- a router response that references template IDs outside the allowed subset, which is now rejected by the validation layer
- a router response that fails validation twice, which now stops the router stage after the single allowed repair attempt
- a request that the mini router marks as ambiguous enough to escalate, which now triggers one additional router call on the stronger model before later steps continue
- an extracted template that matches an existing stored template, which is treated as a safe deduplication hit rather than a hard failure
- a prompt that was expected to be cached but is still queued for generation, which can happen intentionally when `--force` is enabled or when the only prior image rows were failures
- an image prompt that Azure content filters, which now records a per-image failure and lets the remaining serial work continue
- repeated `429` responses from Azure, which now trigger a stop after two consecutive prompts fully exhaust their retries so the run does not keep hammering the endpoint

If the lock belongs to a dead process on the same machine, later runtime slices can recover it automatically through the persistence layer added in TG2.
