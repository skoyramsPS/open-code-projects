"""Backfill missing template metadata through the shared Responses transport."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from comicbook.state import ImportRunState, TemplateImportRow, TemplateImportRowResult, UsageTotals

from pipelines.shared.deps import Deps
from pipelines.workflows.image_prompt_gen.prompts.metadata_prompts import (
    METADATA_BACKFILL_RESPONSE_FORMAT,
    MetadataBackfillResult,
    MetadataBackfillValidationError,
    build_metadata_backfill_messages,
    build_metadata_backfill_payload,
    validate_metadata_backfill_response,
)
from pipelines.workflows.image_prompt_gen.adapters.router_llm import RouterTransportError, call_structured_response

_ESTIMATED_OUTPUT_TOKENS = 80


@dataclass(frozen=True, slots=True)
class _BackfillSuccess:
    metadata: MetadataBackfillResult
    raw_text: str
    input_tokens: int
    output_tokens: int
    router_calls: int


@dataclass(frozen=True, slots=True)
class _BackfillFailure:
    reason: str
    input_tokens: int
    output_tokens: int
    router_calls: int
    transport_exhausted: bool


def _coerce_price(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _lookup_router_token_prices(pricing: object, model: str) -> tuple[float, float]:
    if not isinstance(pricing, dict):
        return 0.0, 0.0

    router_models = pricing.get("router_models")
    if not isinstance(router_models, dict):
        return 0.0, 0.0

    model_entry = router_models.get(model)
    if not isinstance(model_entry, dict):
        return 0.0, 0.0

    input_price = 0.0
    output_price = 0.0
    for key in ("usd_per_1k_input_tokens", "input_usd_per_1k_tokens", "per_1k_input_tokens_usd"):
        price = _coerce_price(model_entry.get(key))
        if price is not None:
            input_price = price
            break
    for key in ("usd_per_1k_output_tokens", "output_usd_per_1k_tokens", "per_1k_output_tokens_usd"):
        price = _coerce_price(model_entry.get(key))
        if price is not None:
            output_price = price
            break
    return input_price, output_price


def _estimate_backfill_call_cost(*, deps: Deps, model: str, payload: dict[str, str]) -> float:
    input_price, output_price = _lookup_router_token_prices(deps.pricing, model)
    if input_price == 0.0 and output_price == 0.0:
        return 0.0

    approximate_input_tokens = max(1, len(payload["name"]) // 4 + len(payload["style_text"]) // 4 + 64)
    return round(
        (approximate_input_tokens / 1000.0) * input_price + (_ESTIMATED_OUTPUT_TOKENS / 1000.0) * output_price,
        6,
    )


def _actual_backfill_cost(*, deps: Deps, model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = _lookup_router_token_prices(deps.pricing, model)
    return round((input_tokens / 1000.0) * input_price + (output_tokens / 1000.0) * output_price, 6)


def _needs_backfill(row: TemplateImportRow) -> bool:
    return bool(row.get("needs_backfill_tags") or row.get("needs_backfill_summary"))


def _has_terminal_failure(row: TemplateImportRow, row_results: list[TemplateImportRowResult]) -> bool:
    row_index = row.get("row_index")
    return any(result.get("row_index") == row_index and result.get("status") == "failed" for result in row_results)


def _append_failure_result(
    *,
    row: TemplateImportRow,
    row_results: list[TemplateImportRowResult],
    reason: str,
) -> None:
    row_results.append(
        {
            "row_index": row.get("row_index"),
            "template_id": row.get("template_id"),
            "status": "failed",
            "reason": reason,
            "warnings": list(row.get("warnings", [])),
            "retry_count": int(row.get("retry_count", 0)),
        }
    )


def _request_metadata_backfill(row: TemplateImportRow, deps: Deps) -> _BackfillSuccess | _BackfillFailure:
    payload = build_metadata_backfill_payload(name=row.get("name") or "", style_text=row.get("style_text") or "")
    model = deps.config.comicbook_import_backfill_model

    total_input_tokens = 0
    total_output_tokens = 0
    router_calls = 0
    validation_error: str | None = None
    previous_response: str | None = None

    for _attempt in range(2):
        router_calls += 1
        try:
            call_result = call_structured_response(
                http_client=deps.http_client,
                config=deps.config,
                model=model,
                response_format=METADATA_BACKFILL_RESPONSE_FORMAT,
                messages=build_metadata_backfill_messages(
                    payload,
                    validation_error=validation_error,
                    previous_response=previous_response,
                ),
                transport=deps.router_transport,
            )
        except RouterTransportError as exc:
            if router_calls >= 2:
                return _BackfillFailure(
                    reason=f"metadata_backfill_failed:{exc}",
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    router_calls=router_calls,
                    transport_exhausted=True,
                )
            continue

        total_input_tokens += call_result.input_tokens
        total_output_tokens += call_result.output_tokens
        previous_response = call_result.output_text

        try:
            metadata = validate_metadata_backfill_response(call_result.output_text)
        except MetadataBackfillValidationError as exc:
            validation_error = str(exc)
            if router_calls >= 2:
                return _BackfillFailure(
                    reason=f"metadata_backfill_failed:{exc}",
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    router_calls=router_calls,
                    transport_exhausted=False,
                )
            continue

        return _BackfillSuccess(
            metadata=metadata,
            raw_text=call_result.output_text,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            router_calls=router_calls,
        )

    return _BackfillFailure(
        reason="metadata_backfill_failed:unreachable_retry_exhaustion",
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        router_calls=router_calls,
        transport_exhausted=False,
    )


def upload_backfill_metadata(state: ImportRunState, deps: Deps) -> dict[str, Any]:
    """Fill missing tags and summaries for rows that passed validation."""

    parsed_rows = [dict(row) for row in list(state.get("parsed_rows") or [])]
    rows_to_process = list(state.get("rows_to_process") or [])
    row_results = list(state.get("row_results") or [])
    usage = UsageTotals.model_validate(state.get("usage") or {})
    no_backfill = bool(state.get("no_backfill", False))
    allow_missing_optional = bool(state.get("allow_missing_optional", False))
    budget_usd = state.get("budget_usd")
    model = deps.config.comicbook_import_backfill_model

    consecutive_transport_failures = 0

    for row_index in rows_to_process:
        row = parsed_rows[row_index]
        if row.get("validation_errors"):
            continue
        if not _needs_backfill(row):
            continue
        if _has_terminal_failure(row, row_results):
            continue

        if no_backfill:
            if allow_missing_optional:
                if row.get("needs_backfill_tags"):
                    row["tags"] = []
                    row["needs_backfill_tags"] = False
                if row.get("needs_backfill_summary"):
                    row["summary"] = (row.get("name") or "")[:240]
                    row["needs_backfill_summary"] = False
            else:
                _append_failure_result(row=row, row_results=row_results, reason="backfill_disabled")
            continue

        if consecutive_transport_failures >= 2:
            _append_failure_result(row=row, row_results=row_results, reason="metadata_backfill_short_circuit")
            continue

        payload = build_metadata_backfill_payload(name=row.get("name") or "", style_text=row.get("style_text") or "")
        estimated_call_cost = _estimate_backfill_call_cost(deps=deps, model=model, payload=payload)
        if budget_usd is not None and usage.estimated_cost_usd + estimated_call_cost > float(budget_usd):
            _append_failure_result(row=row, row_results=row_results, reason="budget_exceeded")
            continue

        outcome = _request_metadata_backfill(row, deps)
        usage = usage.model_copy(
            update={
                "router_calls": usage.router_calls + outcome.router_calls,
                "router_input_tokens": usage.router_input_tokens + outcome.input_tokens,
                "router_output_tokens": usage.router_output_tokens + outcome.output_tokens,
                "estimated_cost_usd": round(
                    usage.estimated_cost_usd
                    + _actual_backfill_cost(
                        deps=deps,
                        model=model,
                        input_tokens=outcome.input_tokens,
                        output_tokens=outcome.output_tokens,
                    ),
                    6,
                ),
            }
        )

        if isinstance(outcome, _BackfillFailure):
            _append_failure_result(row=row, row_results=row_results, reason=outcome.reason)
            consecutive_transport_failures = consecutive_transport_failures + 1 if outcome.transport_exhausted else 0
            continue

        if row.get("needs_backfill_tags"):
            row["tags"] = list(outcome.metadata.tags)
            row["needs_backfill_tags"] = False
        if row.get("needs_backfill_summary"):
            row["summary"] = outcome.metadata.summary
            row["needs_backfill_summary"] = False
        row["backfill_raw"] = outcome.raw_text
        consecutive_transport_failures = 0

    return {
        "parsed_rows": parsed_rows,
        "row_results": row_results,
        "usage": usage,
    }


__all__ = ["upload_backfill_metadata"]
