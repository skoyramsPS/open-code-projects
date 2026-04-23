# Implementation Handoff: Image Prompt Generation Workflow

- Status: in progress
- Last updated: 2026-04-23
- Implementation guide: `docs/planning/Image-prompt-gen-workflow/implementation.md`
- Planning index: `docs/planning/Image-prompt-gen-workflow/index.md`

## Current status summary

This handoff file tracks execution status for the workflow implementation guide.

The first four implementation sessions completed `TG1 Foundation`, `TG2 Persistence and Locking`, and the full `TG3 Router Planning` group across two coherent slices. The repository now contains the initial workflow package, validated config/state/dependency contracts, a reusable SQLite DAO, deterministic template pre-filtering, a reusable Responses API router client, and the router node that handles repair and escalation.

## TaskGroup progress

| TaskGroup | Title | Status | Notes |
|---|---|---|---|
| TG1 | Foundation | completed | Package skeleton, config/state/deps contracts, baseline tests, `.env.example`, `.gitignore`, and workflow foundation docs added. |
| TG2 | Persistence and Locking | completed | Added `comicbook.db`, WAL/schema initialization, one-run-at-a-time lock handling, persistence CRUD helpers, and DAO tests. |
| TG3 | Router Planning | completed | Schema/prefilter/template-loading cluster and the router transport/repair/escalation cluster are both complete. |
| TG4 | Template Persistence and Cache Partitioning | not started | Depends on TG3. |
| TG5 | Serial Image Execution | not started | Depends on TG4. |
| TG6 | Graph, CLI, and Reporting | not started | Depends on TG5. |
| TG7 | Reuse Proof and Repo Protections | not started | Depends on TG6. |
| TG8 | Final Validation and Documentation Closeout | not started | Depends on TG7. |

## Completed in the latest session

- Selected slice: the remaining `TG3 Router Planning` transport cluster.
- Slice chosen because the previous session had already completed the schema/pre-filter/template-loading half of TG3, leaving one coherent transport-focused cluster: the reusable Responses API client plus the router node that performs repair and escalation.
- Implemented `ComicBook/comicbook/router_llm.py` with:
  - router-visible request payload construction
  - stable system/user request message assembly for the Azure Responses API
  - response text and token-usage extraction helpers
  - exactly one repair retry when validation fails
  - request-time verification that `router_model_chosen` matches the model actually called
- Implemented `ComicBook/comicbook/nodes/router.py` to:
  - require `user_prompt` and consume `templates_sent_to_router`
  - call the fallback router model first
  - perform one repair retry when the first response is invalid
  - escalate once from `gpt-5.4-mini` to `gpt-5.4` when the validated first plan sets `needs_escalation=true`
  - accumulate router usage counters in state without starting prompt materialization or template persistence
- Added `ComicBook/tests/test_router_node.py` covering request shape, repair-once behavior, and deterministic escalation to the stronger router model.
- Updated workflow-specific business and developer docs to describe the live router transport, repair policy, escalation behavior, and the new module boundaries.

## Verification evidence

- `uv run --with pytest --with pydantic python -m pytest -q tests/test_router_node.py tests/test_router_validation.py` from `ComicBook/` → `8 passed`.
- `uv run --with pytest --with pydantic python -m pytest -q` from `ComicBook/` → `22 passed`.
- This session followed a direct TDD loop: `tests/test_router_node.py` was added first, the focused scope was run to confirm the missing-module failure, the transport and node modules were implemented, and then both the focused and full current suites were rerun.

## Files changed in this session

- `ComicBook/comicbook/router_llm.py`
- `ComicBook/comicbook/nodes/router.py`
- `ComicBook/tests/test_router_node.py`
- `docs/business/Image-prompt-gen-workflow/index.md`
- `docs/developer/Image-prompt-gen-workflow/index.md`
- `docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`

## Documentation updates

- Updated the documentation triad for this slice where required:
  - planning execution status in this handoff file
  - business-facing router execution, repair, escalation, limits, and troubleshooting notes in `docs/business/Image-prompt-gen-workflow/index.md`
  - developer-facing transport helpers, router node contract, usage accumulation, and test guidance in `docs/developer/Image-prompt-gen-workflow/index.md`
- Index files did not need changes in this session because no new documentation files or slugs were added.
- No ADR was added in this session because this slice implemented the already-approved router transport and escalation behavior from the planning and implementation docs rather than introducing a new architectural tradeoff.

## Blockers or open questions

- No implementation blocker is currently recorded.
- `pytest` is not available as a system module in this environment, so verification used `uv run ...` commands for the test evidence captured above.
- No install, copy, or delete approval was needed for this slice.

## Next recommended slice

- Eligible TaskGroup: `TG4 Template Persistence and Cache Partitioning`
- Recommended slice: complete the first coherent TG4 cluster around prompt composition and prompt fingerprinting.
- Recommended cluster:
  - `ComicBook/comicbook/fingerprint.py`
  - `ComicBook/comicbook/nodes/persist_template.py`
  - `ComicBook/tests/test_fingerprint.py`
  - initial extracted-template coverage needed for deterministic prompt composition
- Rationale: with TG3 fully complete, the next dependency boundary is the deterministic transformation from validated router plans plus stored templates into persisted template rows and rendered prompt/fingerprint data. That cluster is still smaller and cleaner than taking the whole of TG4 at once.
- Boundaries for the next slice:
  - do not start image generation, reporting, CLI wiring, or graph assembly yet
  - reuse `state["plan"]`, `state["templates"]`, and `deps.db.get_templates_by_ids(...)` rather than re-querying router-visible subsets or re-running the router
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
