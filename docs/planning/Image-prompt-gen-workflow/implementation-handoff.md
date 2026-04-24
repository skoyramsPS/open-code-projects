# Implementation Handoff: Image Prompt Generation Workflow

- Status: in progress
- Last updated: 2026-04-23
- Implementation guide: `docs/planning/Image-prompt-gen-workflow/implementation.md`
- Planning index: `docs/planning/Image-prompt-gen-workflow/index.md`

## Current status summary

This handoff file tracks execution status for the workflow implementation guide.

The latest implementation sessions completed `TG1 Foundation`, `TG2 Persistence and Locking`, the full `TG3 Router Planning` group across two coherent slices, the full `TG4 Template Persistence and Cache Partitioning` group across two coherent slices, the full `TG5 Serial Image Execution` group in one cohesive slice, and the full `TG6 Graph, CLI, and Reporting` group across two coherent slices. The repository now contains the initial workflow package, validated config/state/dependency contracts, a reusable SQLite DAO, deterministic template pre-filtering, a reusable Responses API router client, the router node that handles repair and escalation, a persist-template node, deterministic fingerprint helpers, the cache-lookup node that persists prompt rows and partitions cache hits from generation work, a reusable one-image Azure client, the serial image-generation node with resume and rate-limit circuit-breaker handling, the complete workflow graph with runtime gating, and the workflow-specific CLI/library entry point that writes operator-facing report artifacts.

## TaskGroup progress

| TaskGroup | Title | Status | Notes |
|---|---|---|---|
| TG1 | Foundation | completed | Package skeleton, config/state/deps contracts, baseline tests, `.env.example`, `.gitignore`, and workflow foundation docs added. |
| TG2 | Persistence and Locking | completed | Added `comicbook.db`, WAL/schema initialization, one-run-at-a-time lock handling, persistence CRUD helpers, and DAO tests. |
| TG3 | Router Planning | completed | Schema/prefilter/template-loading cluster and the router transport/repair/escalation cluster are both complete. |
| TG4 | Template Persistence and Cache Partitioning | completed | Both coherent TG4 clusters are complete: extracted-template persistence plus deterministic fingerprinting, then prompt-row persistence and cache partitioning. |
| TG5 | Serial Image Execution | completed | Added reusable one-image Azure transport, serial execution node, resume handling, failure persistence, and two-consecutive-429 circuit breaking. |
| TG6 | Graph, CLI, and Reporting | completed | Both coherent TG6 clusters are complete: graph assembly, summary finalization, CLI/library entry, dry-run and budget branching, report artifacts, and the remaining integration coverage. |
| TG7 | Reuse Proof and Repo Protections | not started | Depends on TG6. |
| TG8 | Final Validation and Documentation Closeout | not started | Depends on TG7. |

## Completed in the latest session

- Selected slice: the second coherent `TG6 Graph, CLI, and Reporting` runtime-surface cluster.
- Slice chosen because the first TG6 graph boundary was already complete, making the next smallest meaningful commit the operator-facing runtime layer: CLI/library argument handling, dry-run and budget branching, report artifacts, and the remaining integration coverage.
- Attempted to load `implementation-slice-guard` via the skill tool as requested, but it is not exposed by the runtime skill registry in this environment. The slice was therefore selected by reading and applying the repository-local `implementation-slice-guard` instructions directly from `.opencode/skills/implementation-slice-guard/SKILL.md`.
- Implemented `ComicBook/comicbook/run.py` to:
  - support positional `user_prompt` plus `--run-id`, `--dry-run`, `--force`, `--panels`, `--budget-usd`, and `--redact-prompts`
  - expose `run_once(...)` as the workflow-specific library entry point that maps runtime options into the initial `RunState`
  - load config, pricing, SQLite, and HTTP client dependencies when tests or callers do not inject `Deps` directly
- Extended `ComicBook/comicbook/graph.py` to:
  - add a workflow-specific `runtime_gate` stage after cache lookup
  - estimate remaining image cost from `state["to_generate"]` and configured pricing
  - short-circuit to summary for `dry_run=True` and budget-blocked runs
  - enforce both per-run `budget_usd` and `COMICBOOK_DAILY_BUDGET_USD` before any image API call
- Extended `ComicBook/comicbook/nodes/summarize.py` to:
  - treat budget-blocked runs as terminal `failed` runs
  - write `runs/<run_id>/report.md` and `logs/<run_id>.summary.json`
  - redact prompt text in those artifacts when `redact_prompts=True`
- Updated `ComicBook/comicbook/router_prompts.py` so router validation correctly accepts a newly extracted template ID when the same response selects it.
- Added the remaining TG6 coverage:
  - `ComicBook/tests/test_graph_new_template.py` for the full extracted-template path and report artifact emission
  - `ComicBook/tests/test_budget_guard.py` for run-budget overflow, daily-budget overflow, dry-run/report redaction, exact panel forwarding, and CLI argument parsing

## Verification evidence

- `uv run --with pytest --with pydantic --with httpx python -m pytest -q tests/test_graph_new_template.py tests/test_budget_guard.py` from `ComicBook/` → initial red phase failed on the missing `comicbook.run` module plus missing budget/report behavior, then the green rerun passed with `6 passed`.
- `uv run --with pytest --with pydantic --with httpx python -m pytest -q tests/test_graph_happy.py tests/test_graph_cache_hit.py tests/test_graph_resume.py tests/test_graph_new_template.py tests/test_budget_guard.py tests/test_router_node.py tests/test_router_validation.py` from `ComicBook/` → `17 passed`.
- `uv run --with pytest --with pydantic --with httpx python -m pytest -q` from `ComicBook/` → `48 passed`.
- This session followed a practical TDD loop: the next TG6 runtime-surface tests were added first, the focused scope was run to confirm the missing CLI/runtime/reporting behavior, then the implementation was added and the focused, broader, and full suites were rerun.

## Files changed in this session

- `ComicBook/comicbook/graph.py`
- `ComicBook/comicbook/nodes/summarize.py`
- `ComicBook/comicbook/router_prompts.py`
- `ComicBook/comicbook/run.py`
- `ComicBook/comicbook/state.py`
- `ComicBook/tests/test_graph_new_template.py`
- `ComicBook/tests/test_budget_guard.py`
- `docs/business/Image-prompt-gen-workflow/index.md`
- `docs/developer/Image-prompt-gen-workflow/index.md`
- `docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`

## Documentation updates

- The docs-update gate applied because this slice materially changed workflow behavior by introducing the CLI/library runtime surface, dry-run and budget branching, and persisted report artifacts.
- Updated the documentation triad for this slice where required:
  - planning execution status in this handoff file
  - business-facing runtime, budget, and reporting notes in `docs/business/Image-prompt-gen-workflow/index.md`
  - developer-facing graph/runtime/summarize contracts and updated test guidance in `docs/developer/Image-prompt-gen-workflow/index.md`
- Index files did not need changes in this session because no new documentation files or slugs were added.
- No ADR was added in this session because this slice implemented the already-approved TG6 runtime behavior from the planning and implementation docs rather than introducing a new architectural tradeoff.

## Blockers or open questions

- `pytest` is not available as a system module in this environment, so verification used `uv run ...` commands for the test evidence captured above.
- The repository contains `.opencode/skills/implementation-slice-guard/SKILL.md`, but the runtime skill registry for this session exposed only `pytest-tdd-guard`, `docs-update-guard`, and `workflow-readiness-check`. Slice selection still followed the local skill instructions manually.
- No implementation blocker is currently recorded.
- No install, copy, or delete approval was needed for this slice.

## Next recommended slice

- Eligible TaskGroup: `TG7 Reuse Proof and Repo Protections`
- Recommended slice: begin the first cohesive TG7 reuse-proof cluster.
- Recommended cluster:
  - `ComicBook/examples/single_portrait_graph.py`
  - `ComicBook/tests/test_example_single_portrait.py`
  - any narrow supporting updates needed to prove shared-module reuse without importing `graph.py` or `run.py`
- Rationale: TG6 exit criteria are now satisfied, so the next smallest meaningful step is to prove the reusable-module design with an alternate graph topology before taking on repo-protection enforcement.
- Boundaries for the next slice:
  - import reusable modules only from shared package code
  - do not depend on `comicbook.run` or the current workflow-specific graph assembly
  - keep repo-protection hook work as a separate follow-on cluster if needed for commit size

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
- Completed the first TG6 graph cluster with ingest and summarize nodes, ordered LangGraph assembly, a minimal library entry point with lock handling, and graph-level happy/cache-hit/resume coverage.
- Verified the focused TG6 graph scope and the full current suite after the graph implementation.
- Completed the second TG6 runtime-surface cluster with `run.py`, runtime budget gating, dry-run/report behavior, and the remaining TG6 integration coverage.
- Verified the focused TG6 runtime scope, a broader graph/router regression scope, and the full current suite after the operator-facing runtime implementation.
