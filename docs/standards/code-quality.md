# Code Quality Standards

## Design principles

- follow SOLID principles pragmatically
- prefer composition over deep inheritance
- keep framework-specific code thin
- separate orchestration, domain logic, and infrastructure adapters
- use explicit interfaces around models, persistence, and third-party integrations

## Clean code expectations

- choose names that reveal intent
- keep functions focused and short
- remove dead code and commented-out code
- avoid duplication when a shared abstraction is justified
- refactor in small, behavior-preserving steps

## Python-specific expectations

- prefer type hints for public functions and important internal boundaries
- validate untrusted inputs and external outputs at boundaries
- keep configuration explicit and centralized
- keep side effects easy to locate and test

## Reliability expectations

- handle retries, timeouts, and partial failures intentionally
- prefer idempotent external effects where possible
- make expensive or irreversible actions obvious in code and docs
- write errors that help the next engineer recover quickly
