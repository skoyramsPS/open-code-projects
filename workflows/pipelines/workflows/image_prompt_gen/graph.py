"""Workflow graph assembly and minimal library execution entry point."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from pipelines.shared.deps import Deps
from pipelines.shared.state import UsageTotals, WorkflowError
from pipelines.shared.execution import bind_node, run_graph_with_lock
from pipelines.workflows.image_prompt_gen.nodes import instrument_image_node
from pipelines.workflows.image_prompt_gen.state import RunState
from pipelines.workflows.image_prompt_gen.nodes.cache_lookup import cache_lookup
from pipelines.workflows.image_prompt_gen.nodes.generate_images_serial import generate_images_serial
from pipelines.workflows.image_prompt_gen.nodes.ingest import ingest
from pipelines.workflows.image_prompt_gen.nodes.load_templates import load_templates
from pipelines.workflows.image_prompt_gen.nodes.persist_template import persist_template
from pipelines.workflows.image_prompt_gen.nodes.router import router
from pipelines.workflows.image_prompt_gen.nodes.summarize import summarize


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


@instrument_image_node(
    "runtime_gate",
    complete_fields=lambda _state, delta: {
        "budget_blocked": delta.get("budget_blocked"),
        "estimated_cost_usd": getattr(delta.get("usage"), "estimated_cost_usd", None),
    },
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
    workflow.add_node("ingest", bind_node(ingest, deps))
    workflow.add_node("load_templates", bind_node(load_templates, deps))
    workflow.add_node("router", bind_node(router, deps))
    workflow.add_node("persist_template", bind_node(persist_template, deps))
    workflow.add_node("cache_lookup", bind_node(cache_lookup, deps))
    workflow.add_node("runtime_gate", bind_node(runtime_gate, deps))
    workflow.add_node("generate_images_serial", bind_node(generate_images_serial, deps))
    workflow.add_node("summarize", bind_node(summarize, deps))

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

    return run_graph_with_lock(initial_state, deps, graph_factory=build_workflow_graph)


__all__ = ["build_workflow_graph", "run_workflow", "runtime_gate"]
