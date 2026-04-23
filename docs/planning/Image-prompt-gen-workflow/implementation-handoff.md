# Implementation Handoff: Image Prompt Generation Workflow

- Status: in progress
- Last updated: 2026-04-23
- Implementation guide: `docs/planning/Image-prompt-gen-workflow/implementation.md`
- Planning index: `docs/planning/Image-prompt-gen-workflow/index.md`

## Current status summary

This handoff file tracks execution status for the workflow implementation guide.

The latest implementation sessions completed `TG1 Foundation`, `TG2 Persistence and Locking`, the full `TG3 Router Planning` group across two coherent slices, and the full `TG4 Template Persistence and Cache Partitioning` group across two coherent slices. The repository now contains the initial workflow package, validated config/state/dependency contracts, a reusable SQLite DAO, deterministic template pre-filtering, a reusable Responses API router client, the router node that handles repair and escalation, a persist-template node, deterministic fingerprint helpers, and the cache-lookup node that persists prompt rows and partitions cache hits from generation work.

## TaskGroup progress

| TaskGroup | Title | Status | Notes |
|---|---|---|---|
| TG1 | Foundation | completed | Package skeleton, config/state/deps contracts, baseline tests, `.env.example`, `.gitignore`, and workflow foundation docs added. |
| TG2 | Persistence and Locking | completed | Added `comicbook.db`, WAL/schema initialization, one-run-at-a-time lock handling, persistence CRUD helpers, and DAO tests. |
| TG3 | Router Planning | completed | Schema/prefilter/template-loading cluster and the router transport/repair/escalation cluster are both complete. |
| TG4 | Template Persistence and Cache Partitioning | completed | Both coherent TG4 clusters are complete: extracted-template persistence plus deterministic fingerprinting, then prompt-row persistence and cache partitioning. |
| TG5 | Serial Image Execution | not started | Depends on TG4. |
| TG6 | Graph, CLI, and Reporting | not started | Depends on TG5. |
| TG7 | Reuse Proof and Repo Protections | not started | Depends on TG6. |
| TG8 | Final Validation and Documentation Closeout | not started | Depends on TG7. |

## Completed in the latest session

- Selected slice: the remaining coherent `TG4 Template Persistence and Cache Partitioning` cache-lookup cluster.
- Slice chosen because TG4 was already in progress and the remaining work was a single bounded contract boundary: turn canonicalized router plans into persisted prompt rows and ordered cache classification without starting image generation yet.
- Implemented `ComicBook/comicbook/nodes/cache_lookup.py` to:
  - require `plan`, `templates`, `run_id`, and `started_at`
  - resolve canonical template IDs through `deps.db.get_templates_by_ids(...)`
  - materialize ordered `RenderedPrompt` items by reusing `comicbook.fingerprint.materialize_rendered_prompts(...)`
  - create prompt rows before generation begins via `deps.db.upsert_prompt_if_absent(...)`
  - collapse duplicate fingerprints into one ordered work item for `cache_hits` and `to_generate`
  - classify cache hits only from prior successful generated-image rows, while honoring `force_regenerate`
- Added `ComicBook/tests/test_node_cache_lookup.py` covering cache-hit partitioning, duplicate-prompt collapse, forced regeneration, and the rule that failed image rows do not count as cache hits.
- Updated workflow-specific business and developer docs to describe the completed TG4 cache-preparation boundary and the handoff target for TG5 serial image execution.

## Verification evidence

- `uv run --with pytest --with pydantic python -m pytest -q tests/test_node_cache_lookup.py` from `ComicBook/` → initial red phase confirmed the missing `comicbook.nodes.cache_lookup` module, then green rerun passed with `3 passed`.
- `uv run --with pytest --with pydantic python -m pytest -q tests/test_fingerprint.py tests/test_node_cache_lookup.py tests/test_db.py` from `ComicBook/` → `18 passed`.
- `uv run --with pytest --with pydantic python -m pytest -q` from `ComicBook/` → `34 passed`.
- This session followed a direct TDD loop: `tests/test_node_cache_lookup.py` was added first, the focused scope was run to confirm the expected missing-module failure, the node was implemented, and then focused plus broader suites were rerun.

## Files changed in this session

- `ComicBook/comicbook/nodes/cache_lookup.py`
- `ComicBook/tests/test_node_cache_lookup.py`
- `docs/business/Image-prompt-gen-workflow/index.md`
- `docs/developer/Image-prompt-gen-workflow/index.md`
- `docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`

## Documentation updates

- Updated the documentation triad for this slice where required:
  - planning execution status in this handoff file
  - business-facing cache-preparation, force behavior, and prompt-persistence notes in `docs/business/Image-prompt-gen-workflow/index.md`
  - developer-facing cache-lookup node contracts, duplicate-fingerprint handling, and updated test guidance in `docs/developer/Image-prompt-gen-workflow/index.md`
- Index files did not need changes in this session because no new documentation files or slugs were added.
- No ADR was added in this session because this slice implemented the already-approved TG4 template-persistence and fingerprint behavior from the planning and implementation docs rather than introducing a new architectural tradeoff.

## Blockers or open questions

- No implementation blocker is currently recorded.
- `pytest` is not available as a system module in this environment, so verification used `uv run ...` commands for the test evidence captured above.
- No install, copy, or delete approval was needed for this slice.

## Next recommended slice

- Eligible TaskGroup: `TG5 Serial Image Execution`
- Recommended slice: start the first TG5 serial image execution cluster.
- Recommended cluster:
  - `ComicBook/comicbook/image_client.py`
  - `ComicBook/comicbook/nodes/generate_images_serial.py`
  - `ComicBook/tests/test_image_client.py`
  - `ComicBook/tests/test_node_generate_images_serial.py`
- Rationale: TG4 is complete, so the next smallest coherent slice is the reusable single-image client plus the serial generation node that consumes `to_generate` in order, persists image results, and honors resume behavior without yet doing graph or CLI wiring.
- Boundaries for the next slice:
  - consume `state["to_generate"]` and `state["rendered_prompts_by_fp"]` from TG4 rather than recomputing fingerprints
  - keep image generation strictly serial with one in-flight request at a time and `n=1`
  - add retry, content-filter, and same-run resume handling without starting graph assembly or summary/reporting nodes yet
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
