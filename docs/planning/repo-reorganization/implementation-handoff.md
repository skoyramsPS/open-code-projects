# Implementation Handoff: Repository Reorganization

- Status: TG1 completed, TG2 in progress, TG3 pending, TG4 pending, TG5 pending
- Last updated: 2026-04-25
- Implementation guide: `docs/planning/repo-reorganization/implementation.md`
- Planning index: `docs/planning/repo-reorganization/index.md`
- Business doc: `docs/business/repo-reorganization/index.md`
- Developer doc: `docs/developer/repo-reorganization/index.md`
- ADR: `docs/planning/adr/ADR-0002-repo-reorganization.md`

## Current status summary

The repository has now completed TG1 plus two TG2 slices: the project-root bootstrap and the first shared-module move.

What is true after this session:

- `workflows/pipelines/shared/logging.py` is the tested shared logging foundation for the target tree
- focused shared logging tests now exist under `workflows/tests/shared/test_logging.py`
- `workflows/pyproject.toml` now exists and defines target-tree package discovery plus pytest configuration for running focused scopes from `workflows/`
- `workflows/.env.example` is now the shared environment-template path for the migration
- `workflows/pipelines/shared/config.py` and `workflows/pipelines/shared/deps.py` are now the source of truth for the shared configuration and dependency-container modules
- `workflows/comicbook/config.py` and `workflows/comicbook/deps.py` are the first explicit target-tree compatibility wrappers for legacy imports
- `ComicBook/comicbook/config.py` and `ComicBook/comicbook/deps.py` now act as thin legacy wrappers so the old package root can still resolve the migrated shared modules during TG2
- setup-facing READMEs and repository-reorganization docs now point at the new target-tree project root, env-template path, and current TG2 module-move progress

What is still true after this session:

- the live runtime still resides under `ComicBook/comicbook/`
- the live tests still reside primarily under `ComicBook/tests/`
- most of the runtime module move into `workflows/pipelines/` has not happened yet
- shared modules such as `db.py`, `execution.py`, `fingerprint.py`, `repo_protection.py`, and `runtime_deps.py` still live only under `ComicBook/comicbook/`
- no legacy runtime module imports `pipelines.shared.logging` yet
- compatibility wrappers exist only for `config` and `deps`; graph, node, state, and most other legacy imports still do not have target-tree wrappers yet

## TaskGroup status table

| TaskGroup | Title | Status | Notes |
| --- | --- | --- | --- |
| TG1 | Finalize and verify the shared logging foundation | completed | Shared logging module aligned with the standard, covered by focused pytest scope, and documented across the triad. |
| TG2 | Move package and tests into `workflows/` with compatibility wrappers | in progress | Bootstrap plus the first shared-module move are complete: target-tree project metadata landed, `config.py`/`deps.py` moved into `pipelines.shared`, and the first `workflows/comicbook/` wrappers exist. Most TG2 work is still pending. |
| TG3 | Split shared and workflow-specific state modules | pending | Blocked on TG2 completing the package move. |
| TG4 | Complete structured logging adoption and template-upload naming cleanup | pending | Blocked on TG3. |
| TG5 | Remove compatibility layer, promote reused modules, and close out docs | pending | Blocked on TG4. |

## Last completed slice

### Selected TaskGroup and slice

- **TaskGroup:** TG2
- **Slice:** TG2 shared config/deps move — migrate the shared configuration and dependency-container modules with thin compatibility wrappers

### Why this slice size was chosen

The first unfinished TaskGroup remained TG2, but the remaining work still spans several unrelated shared modules plus both workflows. The local `implementation-slice-guard` skill was present in the repository at `.opencode/skills/implementation-slice-guard/SKILL.md` but was not exposed through the skill tool, so its selection rules were applied manually from that file. Following that guidance, this slice was chosen because `config.py` and `deps.py` are tightly related, share one focused test strategy, and form a small foundational cluster. `repo_protection.py` was intentionally left for a later slice because it has a different subprocess/git-based test strategy.

### Completed work from this session

1. Added `workflows/pipelines/shared/config.py` as the new source-of-truth home for shared configuration loading.
2. Added `workflows/pipelines/shared/deps.py` as the new source-of-truth home for the shared dependency container.
3. Added `workflows/comicbook/config.py` and `workflows/comicbook/deps.py` as the first explicit target-tree compatibility wrappers.
4. Converted `ComicBook/comicbook/config.py` and `ComicBook/comicbook/deps.py` into thin legacy wrappers that bridge to the migrated shared modules while the old package root still needs to function.
5. Added focused target-tree coverage in `workflows/tests/shared/test_config_and_deps.py` for shared-module behavior and wrapper identity.
6. Verified both the new target-tree test scope and the legacy `ComicBook/tests/test_config.py` regression scope pass.
7. Updated repository-reorganization docs and `workflows/README.md` to reflect that TG2 has started the real shared-module move and the compatibility package now exists.

## Files changed in this session

- `workflows/pipelines/shared/config.py`
- `workflows/pipelines/shared/deps.py`
- `workflows/comicbook/__init__.py`
- `workflows/comicbook/config.py`
- `workflows/comicbook/deps.py`
- `workflows/tests/shared/test_config_and_deps.py`
- `ComicBook/comicbook/config.py`
- `ComicBook/comicbook/deps.py`
- `workflows/README.md`
- `docs/business/repo-reorganization/index.md`
- `docs/developer/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/index.md`
- `docs/planning/repo-reorganization/implementation-handoff.md`

## Tests run and results

Primary target-tree verification command run from `workflows/`:

```bash
uv run --project "../ComicBook" --no-sync pytest -c pyproject.toml -q tests/shared/test_config_and_deps.py tests/shared/test_logging.py
```

Result:

- `8 passed in 0.02s`

Legacy-regression verification command run from `ComicBook/`:

```bash
uv run --project "." --no-sync pytest -q tests/test_config.py
```

Result:

- `8 passed in 0.03s`

Additional verification performed:

- confirmed by a red/green cycle that the new target-tree tests initially failed because `pipelines.shared.config` and `pipelines.shared.deps` did not exist yet, then passed after the move and wrapper implementation
- confirmed target-tree compatibility imports resolve through `workflows/comicbook/config.py` and `workflows/comicbook/deps.py`
- confirmed legacy `ComicBook`-root imports still pass the existing config regression scope after the wrapper conversion

## Documentation updated

### Planning

- updated `docs/planning/repo-reorganization/index.md`
- updated this handoff file

### Business

- updated `docs/business/repo-reorganization/index.md`

### Developer

- updated `docs/developer/repo-reorganization/index.md`

### README / setup docs

- updated `workflows/README.md`

### ADR

- no ADR update was needed in this slice because moving `config.py` and `deps.py` followed the already accepted migration plan and did not introduce a new architecture decision

## Blockers or open questions

- No blocker remains for this slice.
- The local `implementation-slice-guard` skill exists in the repository but is not currently loadable through the skill tool, so slice selection used the checked-in skill file directly.
- Direct `pytest` is still unavailable in the shell environment, so verification reused the existing locked `ComicBook` uv project with `--no-sync` to avoid package installation.
- The legacy `ComicBook/comicbook/config.py` and `deps.py` wrappers currently add the sibling `workflows/` directory to `sys.path` so the old package root can keep working while TG2 is incomplete. This is a temporary bridge, not the long-term compatibility mechanism.
- Running Python verification created additional untracked `__pycache__` files under `workflows/`; they were left in place because delete operations are approval-gated in this workflow.

## Exact next recommended slice

### TG2 next slice: move `repo_protection.py` with its script and focused tests

Recommended next implementation slice:

1. move `ComicBook/comicbook/repo_protection.py` into `workflows/pipelines/shared/repo_protection.py`
2. add `workflows/comicbook/repo_protection.py` and any needed legacy wrapper adjustments so both the target tree and old script path keep working
3. add or move focused repo-protection tests under `workflows/tests/shared/`
4. update `ComicBook/scripts/check_do_not_change.py` only as needed for the moved module, while keeping the protected path constant at `ComicBook/DoNotChange` until that asset itself moves later in TG2
5. keep the slice bounded: do **not** move `db.py`, `execution.py`, `runtime_deps.py`, workflow-owned modules, or the TG3 state split yet

Why this next slice is recommended:

- it follows the same "one shared module cluster at a time" pattern as the config/deps slice
- `repo_protection.py` is self-contained and can be verified with a focused subprocess/git test scope without dragging in broader runtime dependencies
- leaving `db.py`, `execution.py`, and `runtime_deps.py` for later avoids mixing multiple dependency chains and test strategies in one commit

Boundaries for the next session:

- do not start TG3+
- do not move workflow-specific graph, run, or node modules yet
- do not move `db.py`, `execution.py`, `fingerprint.py`, or `runtime_deps.py` in the same slice as `repo_protection.py`
- do not remove legacy paths yet
- do not split `state.py` until TG3

## Session log

### 2026-04-24 — Planning session

- Created `docs/planning/repo-reorganization/implementation.md` as the primary implementation document.
- Created the initial `docs/planning/repo-reorganization/implementation-handoff.md` handoff ledger.
- Updated planning indexes for the new implementation material.
- No runtime code changed in that session.

### 2026-04-25 — TG1 implementation session

- Reviewed the implementation guide, current handoff, `workflows/pipelines/shared/logging.py`, the logging standard, and the local `implementation-slice-guard` instructions to choose the next eligible slice.
- Loaded and applied `pytest-tdd-guard` because the slice changed Python behavior in the shared logging module.
- Loaded and applied `docs-update-guard` because the slice materially changed observability infrastructure and developer-facing migration status.
- Completed TG1 as one cohesive slice.
- Added focused logging tests and ran the TG1 pytest scope successfully.
- Updated the planning, business, and developer docs plus ADR-0002 to reflect that implementation has started and TG1 is complete.

### 2026-04-25 — TG2 bootstrap implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice.
- Loaded and applied `docs-update-guard` because this slice changed developer setup expectations and setup-facing documentation.
- Added `workflows/pyproject.toml` and configured target-tree package discovery plus pytest settings for `workflows/`.
- Moved `ComicBook/.env.example` to `workflows/.env.example`.
- Updated setup-facing READMEs plus planning, business, and developer docs to reflect the new target-tree project-root metadata and environment-template path.
- The first verification run exposed that `pipelines` was not importable during pytest collection from `workflows/`; the slice fixed that by adding `pythonpath = ["."]` to `workflows/pyproject.toml`.
- Re-ran the focused target-tree pytest scope successfully from `workflows/`.

### 2026-04-25 — TG2 shared config/deps implementation session

- Reviewed the implementation guide, current handoff, repository state, and the checked-in `implementation-slice-guard` skill file to choose the next eligible commit-sized slice after the bootstrap work.
- Loaded and applied `pytest-tdd-guard` because moving shared modules and adding compatibility wrappers is a Python refactor-risk slice.
- Loaded and applied `docs-update-guard` because the slice changed import/location contracts and maintainer-facing migration status.
- Added a focused target-tree test first; the initial run failed because `pipelines.shared.config` and `pipelines.shared.deps` did not exist yet.
- Added `workflows/pipelines/shared/config.py` and `workflows/pipelines/shared/deps.py` as the new source-of-truth homes for the shared configuration and dependency-container modules.
- Added the first target-tree `workflows/comicbook/` wrappers for `config` and `deps`.
- Converted the legacy `ComicBook/comicbook/config.py` and `deps.py` modules into thin wrappers so the old package root can still resolve the migrated shared modules during TG2.
- Added focused target-tree tests for the shared modules and wrapper identity, then re-ran both target-tree and legacy regression scopes successfully.
- Updated planning, business, developer, and setup docs to reflect that TG2 has started the real shared-module move.

## Permission checkpoint

Stop here.

Do **not** start the next TG2 slice or any other follow-up work until the user explicitly approves another run such as:

`/implement-next docs/planning/repo-reorganization/implementation.md docs/planning/repo-reorganization/implementation-handoff.md`
