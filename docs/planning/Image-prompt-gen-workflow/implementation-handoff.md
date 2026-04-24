# Implementation Handoff: Image Prompt Generation Workflow

- Status: in progress
- Last updated: 2026-04-23
- Implementation guide: `docs/planning/Image-prompt-gen-workflow/implementation.md`
- Planning index: `docs/planning/Image-prompt-gen-workflow/index.md`

## Current status summary

This handoff file tracks execution status for the workflow implementation guide.

The latest implementation sessions completed `TG1 Foundation`, `TG2 Persistence and Locking`, the full `TG3 Router Planning` group across two coherent slices, the full `TG4 Template Persistence and Cache Partitioning` group across two coherent slices, the full `TG5 Serial Image Execution` group in one cohesive slice, the full `TG6 Graph, CLI, and Reporting` group across two coherent slices, and the full `TG7 Reuse Proof and Repo Protections` group across two coherent slices. The repository now contains the initial workflow package, validated config/state/dependency contracts, a reusable SQLite DAO, deterministic template pre-filtering, a reusable Responses API router client, the router node that handles repair and escalation, a persist-template node, deterministic fingerprint helpers, the cache-lookup node that persists prompt rows and partitions cache hits from generation work, a reusable one-image Azure client, the serial image-generation node with resume and rate-limit circuit-breaker handling, the complete workflow graph with runtime gating, the workflow-specific CLI/library entry point that writes operator-facing report artifacts, a reusable execution helper for alternate graphs, and a repository protection check that blocks modifications under `ComicBook/DoNotChange/`.

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
| TG8 | Final Validation and Documentation Closeout | not started | Depends on TG7. |

## Completed in the latest session

- Selected slice: the second coherent `TG7 Reuse Proof and Repo Protections` cluster.
- Slice chosen because TG7 still had one small remaining concern after the reusable-graph proof: enforce the read-only boundary around `ComicBook/DoNotChange/` without pulling TG8 validation work into the same change set.
- The runtime skill registry for this session still did not expose `implementation-slice-guard`, so slice selection continued to follow the repository-local instructions by reading `.opencode/skills/implementation-slice-guard/SKILL.md` directly.
- Added `ComicBook/comicbook/repo_protection.py` with a git-backed helper and CLI entry point that resolves the repository root, inspects `git status --porcelain` for tracked changes under protected paths, and exits nonzero with a readable failure message when `ComicBook/DoNotChange/` files change.
- Added `ComicBook/scripts/check_do_not_change.py` as the repo-local executable wrapper for that protection check.
- Added `.pre-commit-config.yaml` with an always-run local hook that executes `uv run --project ComicBook python ComicBook/scripts/check_do_not_change.py` so the protection check works in this repository's `uv`-based environment.
- Added `ComicBook/tests/test_repo_protection.py` to verify clean repositories, unstaged protected-file edits, and staged protected-file edits.

## Verification evidence

- `uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q tests/test_repo_protection.py` from `ComicBook/` → initial red phase failed with `ModuleNotFoundError: No module named 'comicbook.repo_protection'` plus the missing CLI wrapper path, then the green rerun passed with `3 passed`.
- `uv run --project ComicBook python ComicBook/scripts/check_do_not_change.py` from the repository root → exited successfully with no output while the protected files remained unchanged.
- `uv run --with pytest --with pydantic --with httpx --with langgraph python -m pytest -q` from `ComicBook/` → `53 passed`.
- This session followed a practical TDD loop: the repo-protection test file was added first, the focused scope was run to confirm the missing module and CLI wrapper, then the git-backed protection helper, script wrapper, and hook config were implemented before rerunning focused and full verification.

## Files changed in this session

- `.pre-commit-config.yaml`
- `ComicBook/comicbook/repo_protection.py`
- `ComicBook/scripts/check_do_not_change.py`
- `ComicBook/tests/test_repo_protection.py`
- `docs/business/Image-prompt-gen-workflow/index.md`
- `docs/developer/Image-prompt-gen-workflow/index.md`
- `docs/planning/Image-prompt-gen-workflow/implementation-handoff.md`

## Documentation updates

- The docs-update gate applied because this slice changed developer setup and repository-level operational expectations by adding a required protection hook for read-only reference assets.
- Updated the documentation triad for this slice where required:
  - planning execution status in this handoff file
  - business-facing guardrail and troubleshooting notes in `docs/business/Image-prompt-gen-workflow/index.md`
  - developer-facing hook, module, and verification notes in `docs/developer/Image-prompt-gen-workflow/index.md`
- Index files did not need changes in this session because no new documentation files or slugs were added.
- No ADR was added in this session because the protection hook enforces an existing repository policy without changing workflow architecture, persistence, or public runtime behavior.

## Blockers or open questions

- `pytest` is not available as a system module in this environment, so verification used `uv run ...` commands for the test evidence captured above.
- The repository contains `.opencode/skills/implementation-slice-guard/SKILL.md`, but the runtime skill registry for this session exposed only `pytest-tdd-guard`, `docs-update-guard`, and `workflow-readiness-check`. Slice selection still followed the local skill instructions manually.
- No implementation blocker is currently recorded.
- No install, copy, or delete approval was needed for this slice.

## Next recommended slice

- Eligible TaskGroup: `TG8 Final Validation and Documentation Closeout`
- Recommended slice: start TG8 with final mocked validation evidence and README/operator-usage documentation.
- Recommended cluster:
  - run and capture the full mocked validation scope for final readiness evidence
  - add or update `ComicBook/README.md` usage guidance
  - update any remaining workflow docs to reflect the final shipped runtime surface
- Rationale: TG7 is now complete, so the next smallest meaningful step is to begin release hardening and final acceptance-check closeout.
- Boundaries for the next slice:
  - keep TG8 focused on validation, documentation, and readiness checks rather than new feature work
  - ask for approval before any delete, copy, or package-install step if later validation work would require it

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
