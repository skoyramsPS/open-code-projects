# Image Prompt Generation Workflow

## Status

- Workflow delivery status: in progress
- Current shipped slice: TG2 persistence and locking
- Last updated: 2026-04-23

## What exists today

The repository now contains the reusable foundation for the image prompt generation workflow:

- environment-driven configuration loading with `.env` fallback
- validated state and schema contracts for router plans, prompts, image results, and run summaries
- a frozen dependency container that later workflow nodes will receive explicitly
- a local project layout for tests, examples, run artifacts, logs, and image outputs
- a local SQLite persistence layer with schema initialization, prompt/image/template storage, and daily operator rollups
- one-run-at-a-time protection for a shared workflow database file, including same-host stale-lock recovery when the recorded PID is no longer alive

This slice still does **not** execute the full workflow, but it now establishes the local persistence and operator-safety rules that later routing, caching, image generation, and reporting logic will rely on.

## Expected operator inputs

When later slices are added, operators will provide:

- a free-form user prompt
- Azure OpenAI connection settings
- optional workflow controls such as dry-run, panel count, budget, and resume identifiers

For now, the only supported operational setup is preparing the environment variables documented in `ComicBook/.env.example`.

## Expected outputs later in the workflow

The completed workflow is planned to produce:

- generated images under `image_output/<run_id>/`
- human-readable run reports under `runs/<run_id>/report.md`
- structured summaries under `logs/<run_id>.summary.json`

Those runtime artifacts are not produced yet in this foundation slice.

## Persistence and operator safety now in place

- Workflow data is stored in a local SQLite database file.
- Templates are append-only. Duplicate inserts with the same name and style text are ignored.
- Prompt fingerprints and generated image metadata can now be recorded for later cache and resume behavior.
- Only one active workflow run may hold the database lock at a time.
- If a previous run died on the same host and its PID is no longer alive, the stale lock can be recovered automatically.
- Daily run rollups are now available from the database for cache-hit and estimated-cost reporting.

## Guardrails and limitations

- Secrets are loaded from environment variables first, then `.env`.
- The workflow package does not modify the read-only reference scripts under `ComicBook/DoNotChange/`.
- Router and image API behavior are still not implemented yet.
- The lock policy is intentionally conservative: one active run per SQLite file.
- The package layout is intentionally reusable so later workflows can share the same contracts.

## Plain-language troubleshooting

If setup fails at this stage, the most likely causes are:

- missing Azure configuration, which is reported explicitly by the config loader
- a currently active run already holding the database lock for the chosen SQLite file

If the lock belongs to a dead process on the same machine, later runtime slices can recover it automatically through the persistence layer added in TG2.
