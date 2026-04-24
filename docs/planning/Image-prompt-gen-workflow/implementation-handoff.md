# Implementation Handoff: Image Prompt Generation Workflow

- Status: in progress
- Last updated: 2026-04-23
- Implementation guide: `docs/planning/Image-prompt-gen-workflow/implementation.md`
- Planning index: `docs/planning/Image-prompt-gen-workflow/index.md`

## Current status summary

This handoff file tracks execution status for the workflow implementation guide.

The latest implementation sessions completed `TG1 Foundation`, `TG2 Persistence and Locking`, the full `TG3 Router Planning` group across two coherent slices, the full `TG4 Template Persistence and Cache Partitioning` group across two coherent slices, and the full `TG5 Serial Image Execution` group in one cohesive slice. The repository now contains the initial workflow package, validated config/state/dependency contracts, a reusable SQLite DAO, deterministic template pre-filtering, a reusable Responses API router client, the router node that handles repair and escalation, a persist-template node, deterministic fingerprint helpers, the cache-lookup node that persists prompt rows and partitions cache hits from generation work, a reusable one-image Azure client, and the serial image-generation node with resume and rate-limit circuit-breaker handling.

## TaskGroup progress

| TaskGroup | Title | Status | Notes |
|---|---|---|---|
| TG1 | Foundation | completed | Package skeleton, config/state/deps contracts, baseline tests, `.env.example`, `.gitignore`, and workflow foundation docs added. |
| TG2 | Persistence and Locking | completed | Added `comicbook.db`, WAL/schema initialization, one-run-at-a-time lock handling, persistence CRUD helpers, and DAO tests. |
| TG3 | Router Planning | completed | Schema/prefilter/template-loading cluster and the router transport/repair/escalation cluster are both complete. |
| TG4 | Template Persistence and Cache Partitioning | completed | Both coherent TG4 clusters are complete: extracted-template persistence plus deterministic fingerprinting, then prompt-row persistence and cache partitioning. |
| TG5 | Serial Image Execution | completed | Added reusable one-image Azure transport, serial execution node, resume handling, failure persistence, and two-consecutive-429 circuit breaking. |
| TG6 | Graph, CLI, and Reporting | not started | Depends on TG5. |
| TG7 | Reuse Proof and Repo Protections | not started | Depends on TG6. |
| TG8 | Final Validation and Documentation Closeout | not started | Depends on TG7. |

## Completed in the latest session

- Selected slice: the full coherent `TG5 Serial Image Execution` group.
- Slice chosen because TG4 was complete and the remaining TG5 work was one bounded runtime boundary: a reusable single-image client plus the serial execution node that consumes `to_generate` and persists per-image outcomes without starting graph assembly.
- Implemented `ComicBook/comicbook/image_client.py` to:
  - send deployment-scoped Azure image-generation requests with exactly one prompt per request and `n=1`
  - retry only on `408`, `429`, and `5xx`, up to three total attempts
  - stop retrying on content-filter or other terminal `4xx` responses
  - decode `data[0].b64_json`, create parent directories, and write the image bytes to disk
  - return structured success or failure metadata that stays independent of LangGraph and SQLite
- Implemented `ComicBook/comicbook/nodes/generate_images_serial.py` to:
  - require `run_id`, `to_generate`, and `rendered_prompts_by_fp`
  - process prompts strictly serially in `to_generate` order
  - resume same-run work by skipping the API call when `image_output/<run_id>/<fingerprint>.png` already exists
  - persist `images` rows for generated, failed, and `skipped_rate_limit` outcomes
  - continue after terminal per-image failures instead of aborting the full run
  - stop remaining API calls after two consecutive retry-exhausted `429` prompt failures and record the rest as `skipped_rate_limit`
  - append `ImageResult`, `WorkflowError`, `usage.image_calls`, and `rate_limit_consecutive_failures` updates back into state
- Added `ComicBook/tests/test_image_client.py` covering `429` retry success, request payload and endpoint shape, and terminal content-filter handling.
- Added `ComicBook/tests/test_node_generate_images_serial.py` covering same-run resume behavior, non-retryable failure continuation, and the two-consecutive-429 circuit breaker.
- Updated workflow-specific business and developer docs to describe the completed TG5 execution boundary and the handoff target for TG6 graph, CLI, and reporting work.

## Verification evidence

- `uv run --with pytest --with pydantic --with httpx python -m pytest -q tests/test_image_client.py tests/test_node_generate_images_serial.py` from `ComicBook/` → initial red phase confirmed the missing `comicbook.image_client` and `comicbook.nodes.generate_images_serial` modules, then green rerun passed with `5 passed`.
- `uv run --with pytest --with pydantic --with httpx python -m pytest -q tests/test_db.py tests/test_fingerprint.py tests/test_node_cache_lookup.py tests/test_image_client.py tests/test_node_generate_images_serial.py` from `ComicBook/` → `23 passed`.
- `uv run --with pytest --with pydantic --with httpx python -m pytest -q` from `ComicBook/` → `39 passed`.
- This session followed a direct TDD loop: the TG5 unit tests were added first, the focused scope was run to confirm the expected missing-module failure, the client and node were implemented, and then focused plus broader suites were rerun.

## Files changed in this session

- `ComicBook/comicbook/image_client.py`
- `ComicBook/comicbook/nodes/generate_images_serial.py`
- `ComicBook/tests/test_image_client.py`
- `ComicBook/tests/test_node_generate_images_serial.py`
- `docs/business/Image-prompt-gen-workflow/index.md`
- `docs/developer/Image-prompt-gen-workflow/index.md`
- `docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`

## Documentation updates

- Updated the documentation triad for this slice where required:
  - planning execution status in this handoff file
  - business-facing serial-generation, resume, retry, and rate-limit notes in `docs/business/Image-prompt-gen-workflow/index.md`
  - developer-facing image-client and serial-node contracts plus updated test guidance in `docs/developer/Image-prompt-gen-workflow/index.md`
- Index files did not need changes in this session because no new documentation files or slugs were added.
- No ADR was added in this session because this slice implemented the already-approved TG5 serial execution and rate-limit behavior from the planning and implementation docs rather than introducing a new architectural tradeoff.

## Blockers or open questions

- No implementation blocker is currently recorded.
- `pytest` is not available as a system module in this environment, so verification used `uv run ...` commands for the test evidence captured above.
- No install, copy, or delete approval was needed for this slice.

## Next recommended slice

- Eligible TaskGroup: `TG6 Graph, CLI, and Reporting`
- Recommended slice: start the first TG6 graph-and-entrypoint cluster.
- Recommended cluster:
  - `ComicBook/comicbook/nodes/ingest.py`
  - `ComicBook/comicbook/nodes/summarize.py`
  - `ComicBook/comicbook/graph.py`
  - `ComicBook/tests/test_graph_happy.py`
  - `ComicBook/tests/test_graph_cache_hit.py`
  - `ComicBook/tests/test_graph_resume.py`
- Rationale: TG5 is complete, so the next smallest coherent slice is to wire the already-implemented reusable modules into a minimal end-to-end graph with ingest and summary boundaries before adding the CLI/report surface area.
- Boundaries for the next slice:
  - keep the existing node contracts intact and compose them rather than moving behavior into `graph.py`
  - make the graph honor the already-implemented serial node outputs instead of inferring status from the filesystem
  - delay CLI parsing, report rendering, and budget enforcement until after the graph-level happy, cache-hit, and resume paths are proven
  - continue using DAO methods only from nodes; do not introduce raw SQL outside `comicbook.db`

## Session log

### 2026-04-23

- Created the initial handoff ledger before implementation work began.
- Completed the full TG1 Foundation slice with package scaffolding, validated config/state/deps contracts, baseline tests, and workflow foundation docs.
- Verified `comicbook` imports locally and that the full current pytest scope passes via `uv run`.
- Completed the full TG2 Persistence and Locking slice with the SQLite DAO, one-run-at-a-time lock handling, stale-lock recovery, persistence helpers, and database tests.
- Verified targeted and full current pytest scopes after the persistence implementation.
- Completed the first TG3 Router Planning cluster with the versioned router prompt module, router payload validation helpers, rationale leak guard, deterministic template pre-filtering, and the `load_templates` node.
- Verified targeted router-related tests, a full current-suite rerun, and direct imports of the new router modules.
- Completed the second TG3 Router Planning cluster with the reusable Responses API router client, router-node repair handling, deterministic escalation, and router-node unit tests.
- Verified the focused router test scope and the full current suite after the transport implementation.
- Completed the first TG4 cluster with extracted-template persistence, canonical template-ID normalization on dedup hits, deterministic prompt composition helpers, and fingerprint tests.
- Verified the new focused TG4 test scope, a persistence-coupled focused scope, and the full current suite after the prompt-materialization implementation.
- Completed the second TG4 cluster with prompt-row persistence, duplicate-fingerprint collapse, ordered cache-hit partitioning, and cache-lookup node tests.
- Verified the focused cache-lookup scope, a TG4-plus-database focused scope, and the full current suite after the cache partitioning implementation.
- Completed the full TG5 Serial Image Execution group with the reusable one-image Azure client, ordered serial image node, same-run resume behavior, terminal failure persistence, and the two-consecutive-429 circuit breaker.
- Verified the focused TG5 scope, a TG4-plus-TG5 regression scope, and the full current suite after the serial execution implementation.
