"""Upload workflow graph assembly and internal execution helper."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from pipelines.shared.deps import Deps
from pipelines.shared.execution import bind_node
from pipelines.workflows.template_upload.nodes import instrument_template_upload_node
from pipelines.workflows.template_upload.state import ImportRunState
from pipelines.workflows.template_upload.nodes.backfill_metadata import backfill_metadata
from pipelines.workflows.template_upload.nodes.decide_write_mode import decide_write_mode
from pipelines.workflows.template_upload.nodes.load_file import load_file
from pipelines.workflows.template_upload.nodes.parse_and_validate import parse_and_validate
from pipelines.workflows.template_upload.nodes.persist import persist
from pipelines.workflows.template_upload.nodes.resume_filter import resume_filter
from pipelines.workflows.template_upload.nodes.summarize import summarize


@instrument_template_upload_node(
    "prepare_deferred_retry",
    complete_fields=lambda _state, delta: {
        "rows_to_process": len(delta.get("rows_to_process", [])),
        "deferred_rows": len(delta.get("deferred_rows", [])),
    },
)
def _prepare_deferred_retry(state: ImportRunState, _deps: Deps) -> dict[str, object]:
    deferred_rows = list(state.get("deferred_rows") or [])
    return {
        "rows_to_process": deferred_rows,
        "deferred_rows": [],
        "allow_defer": False,
    }


def _route_after_persist(state: ImportRunState) -> str:
    if state.get("allow_defer", True) and state.get("deferred_rows"):
        return "prepare_deferred_retry"
    return "summarize"


def build_upload_graph(deps: Deps):
    """Compile the ordered template-upload workflow graph."""

    workflow = StateGraph(ImportRunState)
    workflow.add_node("load_file", bind_node(load_file, deps))
    workflow.add_node("parse_and_validate", bind_node(parse_and_validate, deps))
    workflow.add_node("resume_filter", bind_node(resume_filter, deps))
    workflow.add_node("backfill_metadata", bind_node(backfill_metadata, deps))
    workflow.add_node("decide_write_mode", bind_node(decide_write_mode, deps))
    workflow.add_node("persist", bind_node(persist, deps))
    workflow.add_node("prepare_deferred_retry", bind_node(_prepare_deferred_retry, deps))
    workflow.add_node("summarize", bind_node(summarize, deps))

    workflow.add_edge(START, "load_file")
    workflow.add_edge("load_file", "parse_and_validate")
    workflow.add_edge("parse_and_validate", "resume_filter")
    workflow.add_edge("resume_filter", "backfill_metadata")
    workflow.add_edge("backfill_metadata", "decide_write_mode")
    workflow.add_edge("decide_write_mode", "persist")
    workflow.add_conditional_edges(
        "persist",
        _route_after_persist,
        {
            "prepare_deferred_retry": "prepare_deferred_retry",
            "summarize": "summarize",
        },
    )
    workflow.add_edge("prepare_deferred_retry", "decide_write_mode")
    workflow.add_edge("summarize", END)
    return workflow.compile()


def run_upload_workflow(initial_state: ImportRunState, deps: Deps) -> ImportRunState:
    """Run the compiled upload graph with caller-prepared import state."""

    prepared_state = dict(initial_state)
    prepared_state.setdefault("row_results", [])
    prepared_state.setdefault("errors", [])
    prepared_state.setdefault("usage", {})
    prepared_state.setdefault("allow_defer", True)
    return build_upload_graph(deps).invoke(prepared_state)


__all__ = ["build_upload_graph", "run_upload_workflow"]
