# Implementation Handoff: Image Prompt Generation Workflow

- Status: in progress
- Last updated: 2026-04-23
- Implementation guide: `docs/planning/Image-prompt-gen-workflow/implementation.md`
- Planning index: `docs/planning/Image-prompt-gen-workflow/index.md`

## Current status summary

This handoff file tracks execution status for the workflow implementation guide.

The latest implementation sessions completed `TG1 Foundation`, `TG2 Persistence and Locking`, the full `TG3 Router Planning` group across two coherent slices, the full `TG4 Template Persistence and Cache Partitioning` group across two coherent slices, the full `TG5 Serial Image Execution` group in one cohesive slice, the full `TG6 Graph, CLI, and Reporting` group across two coherent slices, the full `TG7 Reuse Proof and Repo Protections` group across two coherent slices, and the first coherent `TG8 Final Validation and Documentation Closeout` cluster. The repository now contains the workflow package, validated config/state/dependency contracts, a reusable SQLite DAO, deterministic template pre-filtering, a reusable Responses API router client, the router node that handles repair and escalation, a persist-template node, deterministic fingerprint helpers, the cache-lookup node that persists prompt rows and partitions cache hits from generation work, a reusable one-image Azure client, the serial image-generation node with resume and rate-limit circuit-breaker handling, the complete workflow graph with runtime gating, the workflow-specific CLI/library entry point that writes operator-facing report artifacts, a reusable execution helper for alternate graphs, a repository protection check that blocks modifications under `ComicBook/DoNotChange/`, and package-local/operator-facing usage documentation in `ComicBook/README.md`.

## TaskGroup progress

| TaskGroup | Title | Status | Notes |
|---|---|---|---|
| TG1 | Foundation | completed | Package skeleton, config/state/deps contracts, baseline tests, `.env.example`, `.gitignore`, and workflow foundation docs added. |
| TG2 | Persistence and Locking | completed | Added `comicbook.db`, WAL/schema initialization, one-run-at-a-time lock handling, persistence CRUD helpers, and DAO tests. |
| TG3 | Router Planning | completed | Schema/prefilter/template-loading cluster and the router transport/repair/escalation cluster are both complete. |
| TG4 | Template Persistence and Cache Partitioning | completed | Both coherent TG4 clusters are complete: extracted-template persistence plus deterministic fingerprinting, then prompt-row persistence and cache partitioning. |
| TG5 | Serial Image Execution | completed | Added reusable one-image Azure transport, serial execution node, resume handling, failure persistence, and two-consecutive-429 circuit breaking. |
| TG6 | Graph, CLI, and Reporting | completed | Both coherent TG6 clusters are complete: graph assembly, summary finalization, CLI/library entry, dry-run and budget branching, report artifacts, and the remaining integration coverage. |
| TG7 | Reuse Proof and Repo Protections | completed | Both cohesive TG7 clusters are complete: reusable alternate-graph proof, shared-module import fence, and git-backed repository protection for `ComicBook/DoNotChange/`. |
| TG8 | Final Validation and Documentation Closeout | in progress | Mocked full-suite validation, acceptance-evidence mapping, README usage guidance, and workflow-doc updates are complete; live smoke evidence remains pending explicit opt-in. |

## Completed in the latest session

- Selected slice: the first coherent `TG8 Final Validation and Documentation Closeout` cluster.
- Exact slice completed: run the full mocked validation suite, verify the acceptance checklist item-by-item from existing evidence, add/update package-local usage instructions, and update workflow-specific business/developer docs to match the shipped runtime surface.
- Slice chosen because TG8 contains one externally gated task (`perform one documented live smoke test behind an explicit opt-in flag`) that should not be mixed into the same commit-sized session as validation/documentation work when no opt-in was provided. The mocked-validation-and-docs cluster is still a meaningful shippable increment and keeps the remaining work to one final externally approved step.
- The runtime skill registry for this session still did not expose `implementation-slice-guard`, so slice selection again followed the repository-local instructions by reading `.opencode/skills/implementation-slice-guard/SKILL.md` directly.
- Added `ComicBook/README.md` with setup guidance, CLI and library usage examples, output locations, operator notes, and the current live-smoke expectation.
- Added `ComicBook/tests/test_node_ingest_summarize.py` so the remaining uncovered node modules now have direct unit tests that do not import `graph.py`.
- Updated the workflow business documentation to reflect the completed TG7 state, the current validation snapshot, and the operator-facing runtime usage flow.
- Updated the workflow developer documentation with the TG8 validation command/result, acceptance-evidence mapping, and README references.
- Verified the current acceptance checklist items one by one against the mocked test suite, direct runtime surfaces, and the existing repository protections, and recorded the remaining live-smoke gap below.

## Verification evidence

- `uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q tests/test_node_ingest_summarize.py` from `ComicBook/` → `2 passed`.
- `uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q` from `ComicBook/` → `55 passed`.
- `uv run python -c "from comicbook.config import load_config; cfg = load_config('.env'); print(cfg.azure_openai_chat_deployment, cfg.azure_openai_image_deployment)"` from `ComicBook/` currently raises `ConfigError: Missing required configuration values: AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_IMAGE_DEPLOYMENT`, so the live smoke cannot run until those required deployment names are supplied in the local config surface.
- `ComicBook/README.md` was cross-checked against the shipped CLI surface in `ComicBook/comicbook/run.py`, the artifact-writing behavior in `ComicBook/comicbook/nodes/summarize.py`, and the environment contract in `ComicBook/.env.example`.
- No Python behavior changed in this slice, so `pytest-tdd-guard` was not required; however, the full mocked regression suite was still rerun to provide final-validation evidence for TG8.

## Acceptance checklist status

| Acceptance item | Status | Evidence |
|---|---|---|
| `python -m comicbook.run "<prompt>"` produces images under `image_output/<run_id>/`. | mocked evidence complete | `tests/test_graph_happy.py` exercises `run_workflow(...)` end to end and verifies generated image output files under the configured output directory; `ComicBook/README.md` now documents the CLI invocation surface. |
| A `runs` row is written with the correct terminal status. | complete | `tests/test_graph_happy.py`, `tests/test_graph_cache_hit.py`, `tests/test_budget_guard.py`, and `tests/test_graph_resume.py` assert persisted final run status behavior. |
| Image generation is observably serial and always uses `n=1`. | complete | `tests/test_image_client.py` verifies `n=1`; `tests/test_node_generate_images_serial.py` verifies ordered serial execution and continuation behavior. |
| Re-running the same prompt without `--force` produces cache hits and zero new image API calls. | complete | `tests/test_graph_cache_hit.py`. |
| `--dry-run` produces a plan and report without calling the image API. | complete | `tests/test_budget_guard.py`. |
| Resuming with the same `--run-id` generates only the missing images. | complete | `tests/test_graph_resume.py`. |
| Router schema failures trigger exactly one repair attempt. | complete | `tests/test_router_node.py`, `tests/test_router_validation.py`. |
| Router escalation behavior is covered by tests. | complete | `tests/test_router_node.py`. |
| Every node module has at least one direct unit test that does not import `graph.py`. | complete | direct node tests now exist for `load_templates`, `router`, `persist_template`, `cache_lookup`, `generate_images_serial`, plus the newly added `tests/test_node_ingest_summarize.py` for `ingest` and `summarize`. |
| `examples/single_portrait_graph.py` works without modifying the reusable modules. | complete | `tests/test_example_single_portrait.py`. |
| `ComicBook/DoNotChange/` files are unchanged. | complete | repository protection check and `tests/test_repo_protection.py`; no modified files under that path in current repo state. |
| Budget guards prevent image generation when the budget would be exceeded. | complete | `tests/test_budget_guard.py`. |
| Human-readable and structured summary artifacts are written to disk. | complete | `tests/test_graph_new_template.py`, `tests/test_budget_guard.py`, `comicbook/nodes/summarize.py`. |
| One live smoke test result is documented. | pending explicit opt-in | TG8 requires a real Azure smoke invocation, but no explicit opt-in was provided for this session. |

## Files changed in this session

- `ComicBook/README.md`
- `ComicBook/tests/test_node_ingest_summarize.py`
- `docs/business/Image-prompt-gen-workflow/index.md`
- `docs/developer/Image-prompt-gen-workflow/index.md`
- `docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`

## Documentation updates

- The docs-update gate applied because this slice materially updated workflow-specific operator and maintainer documentation, added the package README referenced by `ComicBook/pyproject.toml`, and recorded TG8 validation evidence needed for release readiness.
- Updated the documentation triad for this slice where required:
  - planning execution status in this handoff file
  - business-facing validation snapshot and runtime usage notes in `docs/business/Image-prompt-gen-workflow/index.md`
  - developer-facing validation evidence, acceptance mapping, and README references in `docs/developer/Image-prompt-gen-workflow/index.md`
  - package-local usage and operator guidance in `ComicBook/README.md`
- Index files did not need changes in this session because no new documentation files were added under `docs/` and no workflow slug changed.
- No ADR was added in this session because the work did not change workflow architecture, persistence strategy, or runtime contracts; it documented the already shipped implementation surface and its validation status.

## Blockers or open questions

- `pytest` is not available as a system module in this environment, so verification used `uv run ...` commands for the test evidence captured above.
- The repository contains `.opencode/skills/implementation-slice-guard/SKILL.md`, but the runtime skill registry for this session exposed only `pytest-tdd-guard`, `docs-update-guard`, and `workflow-readiness-check`. Slice selection still followed the local skill instructions manually.
- TG8 still requires one live Azure smoke result, but that step is intentionally gated behind explicit opt-in and was not executed in this session.
- The current local config surface is also not yet live-smoke ready: `load_config('.env')` fails because `AZURE_OPENAI_CHAT_DEPLOYMENT` and `AZURE_OPENAI_IMAGE_DEPLOYMENT` are missing.
- No install, copy, or delete approval was needed for this slice.

## Next recommended slice

- Eligible TaskGroup: `TG8 Final Validation and Documentation Closeout`
- Recommended slice: finish TG8 with the explicit live-smoke and final readiness closeout.
- Recommended cluster:
  - obtain explicit opt-in for real Azure traffic and ensure the required chat/image deployment names are configured locally
  - run one documented live smoke invocation
  - record the exact command, environment assumptions, run ID, and result in this handoff
  - reconcile any live-only deviations in docs or a follow-up change note if the smoke uncovers a mismatch
  - optionally use `workflow-readiness-check` before declaring the workflow ready to ship
- Rationale: the mocked validation-and-docs cluster is now complete, so the only meaningful remaining TG8 work is the externally gated live validation step and any final closeout it drives.
- Boundaries for the next slice:
  - do not add new workflow features while closing out TG8
  - ask for approval before any delete, copy, or package-install step if later validation work would require it
  - do not perform the live smoke unless the user explicitly opts in to real Azure usage and the missing deployment config has been supplied

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
- Completed the first TG7 reuse-proof cluster with a shared execution helper, an alternate single-portrait example graph, and modularity regression coverage proving shared modules do not import `comicbook.graph` or `comicbook.run`.
- Verified the focused TG7 example scope, the broader graph regression scope, and the full current suite after the reuse-proof implementation.
- Completed the second TG7 repo-protection cluster with a git-backed `ComicBook/DoNotChange/` protection helper, a `uv`-backed local pre-commit hook, and targeted tests for clean, unstaged-change, and staged-change enforcement.
- Verified the focused TG7 protection scope, a direct standalone protection-check invocation, and the full current suite after the repository-protection implementation.
- Completed the first TG8 closeout cluster with a full mocked suite rerun, acceptance-check evidence mapping, direct unit tests for the remaining uncovered node modules (`ingest` and `summarize`), `ComicBook/README.md` usage guidance, and workflow business/developer doc updates.
- Verified the focused direct-node scope (`2 passed`) and the full mocked workflow test suite again (`55 passed`), leaving only the explicitly opt-in live smoke step as the remaining TG8 gap.
