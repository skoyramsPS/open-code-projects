# Logging Standards

This repository ships one logging module that every workflow, node, and shared module uses. Consistency is more important than cleverness — the goal is that any log line, from any workflow, can be filtered by the same handful of fields.

## Design rules

- one shared logging module owns all logger construction and formatting
- the standard library is the only logging dependency
- every log line is a structured JSON object on stdout
- a small set of always-present fields makes logs filterable across workflows
- nodes do not call `logging.getLogger` directly; they receive a logger through `Deps`
- a node helper writes the canonical event line so individual nodes do not re-implement field plumbing

## Required fields

Every record emitted through the shared logging module must include:

- `timestamp` — ISO-8601 UTC, millisecond precision
- `level` — standard logging level name (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `logger` — dotted logger name (e.g. `pipelines.workflows.image_prompt_gen.run`)
- `event` — short snake_case event name describing what happened
- `workflow` — workflow slug (e.g. `image_prompt_gen`, `template_upload`) or `shared` for cross-cutting code
- `run_id` — the active run identifier when one exists, otherwise `null`
- `message` — human-readable summary of the event

Optional but encouraged when applicable:

- `node` — node name when the line originates inside a graph node
- `component` — module path or subsystem name when the line is outside a node (`db`, `router_llm`, `cli`, `http_client`, …)
- `duration_ms` — when the line marks the end of a measurable operation
- `error.code`, `error.message`, `error.retryable` — when the line records a failure
- `extra` — free-form object for workflow-specific fields; keys must be snake_case

Sensitive fields (prompt text, API keys, full row payloads) must not appear unless the caller has explicitly opted in. Honor existing redaction flags such as `redact_prompts` and `redact_style_text_in_logs`.

## Module location and shape

The shared module lives at `workflows/pipelines/shared/logging.py` and exposes:

- `get_logger(name: str) -> logging.Logger` — returns a logger that uses the shared JSON formatter and a single stdout handler. Idempotent.
- `JsonFormatter` — `logging.Formatter` subclass that serializes records as JSON with the required fields above.
- `NodeLogContext` — small dataclass carrying `workflow`, `run_id`, and optional `node` for the duration of a graph run.
- `log_node_event(deps, state, event, *, level="INFO", message=None, **fields) -> None` — node-facing helper that resolves `workflow`/`run_id` from state, sets `node` from the calling frame or an explicit kwarg, and emits one structured line through `deps.logger`.

The module must work without any third-party dependency. Console-readable formatting for local development is opt-in via an environment variable (`PIPELINES_LOG_FORMAT=text`); the default is JSON so production and CI logs stay machine-parseable.

## How nodes use the logger

A node receives `deps` as today. The logger is reached through `deps.logger` only via the helper:

```python
from pipelines.shared.logging import log_node_event

def my_node(state, deps):
    log_node_event(deps, state, "node_started", input_count=len(state["rows"]))
    ...
    log_node_event(
        deps,
        state,
        "node_completed",
        level="INFO",
        rows_written=written,
        duration_ms=elapsed_ms,
    )
    return delta
```

Direct calls like `deps.logger.info(...)` are discouraged inside nodes because they bypass field enforcement. They are acceptable in CLI entry points, runtime-deps construction, and shared infrastructure modules where there is no node context.

## How non-node code uses the logger

Outside of nodes, modules call `get_logger(__name__)` once at import time and log through that logger. The JSON formatter still fills `timestamp`, `level`, `logger`, and (when set on the record's `extra`) the standard fields. Use `logger.info("event_name", extra={"event": "event_name", "workflow": "shared", "component": "db", ...})` so the output stays consistent with node-emitted lines.

A small convenience wrapper, `log_event(logger, event, *, workflow="shared", run_id=None, **fields)`, will live alongside `log_node_event` so non-node modules do not have to remember the `extra` shape.

## Levels

- `DEBUG` — verbose internal detail useful only when diagnosing a specific run
- `INFO` — normal lifecycle events: node start/end, write decisions, cache hits, summary computed
- `WARNING` — recoverable issues, deferred rows, retry attempts, budget approaching
- `ERROR` — non-recoverable failures within the current operation
- `CRITICAL` — process-level failures that should page a human

Default runtime level is `INFO`. Set `PIPELINES_LOG_LEVEL=DEBUG` to widen the floor.

## Testing expectations

- the JSON formatter has direct unit tests covering required fields and optional fields
- `log_node_event` has a unit test that asserts `workflow`, `run_id`, `node`, and `event` are populated from state and call site
- node tests do not assert on log text; they assert behavior. Logs are observed only in dedicated logging tests.
- the shared logger is configured once per process; tests reset handlers between cases to avoid duplicate output

## Reuse rule

If a workflow needs logging behavior that is not in the shared module, extend the shared module instead of adding a parallel logger. New fields land in the standard before they appear in workflow code.
