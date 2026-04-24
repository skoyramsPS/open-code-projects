"""Workflow graph assembly and minimal library execution entry point."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Callable

from langgraph.graph import END, START, StateGraph

from comicbook.deps import Deps
from comicbook.nodes.cache_lookup import cache_lookup
from comicbook.nodes.generate_images_serial import generate_images_serial
from comicbook.nodes.ingest import ingest
from comicbook.nodes.load_templates import load_templates
from comicbook.nodes.persist_template import persist_template
from comicbook.nodes.router import router
from comicbook.nodes.summarize import summarize
from comicbook.state import RunState, UsageTotals, WorkflowError


NodeCallable = Callable[[RunState, Deps], dict[str, object]]


def _bind(node: NodeCallable, deps: Deps) -> Callable[[RunState], dict[str, object]]:
    return lambda state, fn=node: fn(state, deps)


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _format_timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc) if value.tzinfo is not None else value
    rendered = normalized.replace(microsecond=0).isoformat()
    return rendered.replace("+00:00", "Z") if value.tzinfo is not None else f"{rendered}Z"


def _prepare_initial_state(state: RunState, deps: Deps) -> RunState:
    prepared = dict(state)
    prepared.update(ingest(state, deps))
    return prepared


def _coerce_price(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _lookup_image_price(pricing: object, image_model: str) -> float:
    if not isinstance(pricing, dict):
        return 0.0

    image_models = pricing.get("image_models")
    if isinstance(image_models, dict):
        model_entry = image_models.get(image_model)
        if isinstance(model_entry, dict):
            for key in ("usd_per_image", "per_image_usd", "cost_usd"):
                price = _coerce_price(model_entry.get(key))
                if price is not None:
                    return price
        price = _coerce_price(model_entry)
        if price is not None:
            return price

    legacy_image = pricing.get("image")
    if isinstance(legacy_image, dict):
        model_entry = legacy_image.get(image_model)
        if isinstance(model_entry, dict):
            for key in ("usd_per_image", "per_image_usd", "cost_usd"):
                price = _coerce_price(model_entry.get(key))
                if price is not None:
                    return price
        price = _coerce_price(model_entry)
        if price is not None:
            return price

    return 0.0


def _estimate_run_cost(state: RunState, deps: Deps) -> float:
    usage = UsageTotals.model_validate(state.get("usage") or {})
    estimate = usage.estimated_cost_usd
    for prompt in state.get("to_generate", []):
        estimate += _lookup_image_price(deps.pricing, prompt.image_model)
    return estimate


def _build_budget_error(*, message: str, est_cost_usd: float, limit_usd: float) -> WorkflowError:
    return WorkflowError.model_validate(
        {
            "code": "budget_guard",
            "message": message,
            "node": "graph",
            "retryable": False,
            "details": {
                "estimated_cost_usd": round(est_cost_usd, 6),
                "limit_usd": round(limit_usd, 6),
            },
        }
    )


def runtime_gate(state: RunState, deps: Deps) -> dict[str, object]:
    """Compute cost estimates and decide whether runtime guards block generation."""

    usage = UsageTotals.model_validate(state.get("usage") or {})
    updated_usage = usage.model_copy(update={"estimated_cost_usd": _estimate_run_cost(state, deps)})
    existing_errors = list(state.get("errors", []))

    if state.get("dry_run", False):
        return {
            "usage": updated_usage,
            "budget_blocked": False,
        }

    estimated_cost = updated_usage.estimated_cost_usd
    run_budget = state.get("budget_usd")
    if run_budget is not None and estimated_cost > float(run_budget):
        return {
            "usage": updated_usage,
            "budget_blocked": True,
            "errors": existing_errors
            + [
                _build_budget_error(
                    message=(
                        f"Estimated run cost ${estimated_cost:.2f} exceeds the configured run budget ${float(run_budget):.2f}."
                    ),
                    est_cost_usd=estimated_cost,
                    limit_usd=float(run_budget),
                )
            ],
        }

    daily_budget = deps.config.comicbook_daily_budget_usd
    started_at = state.get("started_at")
    if daily_budget is not None and started_at:
        rollup = deps.db.get_daily_budget_rollup(started_at[:10])
        spent_today = rollup.total_est_cost_usd if rollup is not None else 0.0
        projected_total = spent_today + estimated_cost
        if projected_total > daily_budget:
            return {
                "usage": updated_usage,
                "budget_blocked": True,
                "errors": existing_errors
                + [
                    _build_budget_error(
                        message=(
                            f"Estimated run cost would push the daily budget to ${projected_total:.2f}, "
                            f"above the configured daily budget ${daily_budget:.2f}."
                        ),
                        est_cost_usd=projected_total,
                        limit_usd=daily_budget,
                    )
                ],
            }

    return {
        "usage": updated_usage,
        "budget_blocked": False,
    }


def _route_after_runtime_gate(state: RunState) -> str:
    if state.get("dry_run", False) or state.get("budget_blocked", False):
        return "summarize"
    return "generate_images_serial"


def build_workflow_graph(deps: Deps):
    """Compile the ordered v1 workflow graph from the current reusable nodes."""

    workflow = StateGraph(RunState)
    workflow.add_node("ingest", _bind(ingest, deps))
    workflow.add_node("load_templates", _bind(load_templates, deps))
    workflow.add_node("router", _bind(router, deps))
    workflow.add_node("persist_template", _bind(persist_template, deps))
    workflow.add_node("cache_lookup", _bind(cache_lookup, deps))
    workflow.add_node("runtime_gate", _bind(runtime_gate, deps))
    workflow.add_node("generate_images_serial", _bind(generate_images_serial, deps))
    workflow.add_node("summarize", _bind(summarize, deps))

    workflow.add_edge(START, "ingest")
    workflow.add_edge("ingest", "load_templates")
    workflow.add_edge("load_templates", "router")
    workflow.add_edge("router", "persist_template")
    workflow.add_edge("persist_template", "cache_lookup")
    workflow.add_edge("cache_lookup", "runtime_gate")
    workflow.add_conditional_edges(
        "runtime_gate",
        _route_after_runtime_gate,
        {
            "generate_images_serial": "generate_images_serial",
            "summarize": "summarize",
        },
    )
    workflow.add_edge("generate_images_serial", "summarize")
    workflow.add_edge("summarize", END)
    return workflow.compile()


def run_workflow(initial_state: RunState, deps: Deps) -> RunState:
    """Run the current workflow graph with lock acquisition and failure finalization."""

    prepared_state = _prepare_initial_state(initial_state, deps)
    run_id = prepared_state["run_id"]
    user_prompt = prepared_state["user_prompt"]
    started_at = prepared_state["started_at"]

    deps.db.acquire_run_lock(
        run_id=run_id,
        user_prompt=user_prompt,
        started_at=started_at,
        pid=deps.pid_provider(),
        host=deps.hostname_provider(),
        router_prompt_version=deps.config.comicbook_router_prompt_version,
        pid_is_alive=_pid_is_alive,
    )

    graph = build_workflow_graph(deps)
    try:
        return graph.invoke(prepared_state)
    except Exception:
        run_record = deps.db.get_run(run_id)
        if run_record is not None and run_record.status == "running":
            deps.db.finalize_run(
                run_id=run_id,
                ended_at=_format_timestamp(deps.clock()),
                status="failed",
                cache_hits=0,
                generated=0,
                failed=0,
                skipped_rate_limit=0,
                est_cost_usd=0.0,
                router_prompt_version=deps.config.comicbook_router_prompt_version,
            )
        raise


__all__ = ["build_workflow_graph", "run_workflow", "runtime_gate"]
