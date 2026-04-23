# Testing and TDD Standards

## Default stack

- use `pytest` as the default test runner
- prefer `tests/` as the top-level test directory unless a package already uses a stronger local convention
- default quick command: `pytest -q`

## TDD loop

Follow red, green, refactor when practical:

1. write the smallest failing test that captures the behavior
2. implement the smallest change that makes it pass
3. refactor while keeping tests green

If strict TDD is not practical, add or update the test before marking the work complete and say why the loop was adapted.

## Required test expectations

- every behavior change must add or update tests
- every bug fix must add a regression test
- risky refactors must preserve or improve coverage for affected behavior
- missing tests block completion unless explicitly waived with a reason

## LangGraph-specific expectations

- unit test reusable helpers and node logic directly
- integration test graph assembly, routing, persistence, interrupts, and retry behavior when relevant
- mock LLM, network, filesystem, and external tool boundaries in unit tests
- keep a small number of high-value end-to-end tests for critical workflows

## Pytest conventions

- name files `test_*.py`
- keep fixtures readable and close to the tests that use them
- prefer deterministic assertions over snapshot sprawl
- use parametrization for pure logic with multiple cases
- keep narrow test scopes fast; broaden only when needed

## Completion gate

Before a change is done, report:

- what behavior changed
- which tests were added or updated
- what pytest scope was run
- what risks or coverage gaps remain
