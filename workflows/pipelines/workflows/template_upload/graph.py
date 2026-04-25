"""Upload workflow graph assembly and internal execution helper."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from comicbook.nodes.upload_backfill_metadata import upload_backfill_metadata
from comicbook.nodes.upload_decide_write_mode import upload_decide_write_mode
from comicbook.nodes.upload_load_file import upload_load_file
from comicbook.nodes.upload_parse_and_validate import upload_parse_and_validate
from comicbook.nodes.upload_persist import upload_persist
from comicbook.nodes.upload_resume_filter import upload_resume_filter
from comicbook.nodes.upload_summarize import upload_summarize
from comicbook.state import ImportRunState

from pipelines.shared.deps import Deps
from pipelines.shared.execution import bind_node


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
    return "upload_summarize"


def build_upload_graph(deps: Deps):
    """Compile the ordered template-upload workflow graph."""

    workflow = StateGraph(ImportRunState)
    workflow.add_node("upload_load_file", bind_node(upload_load_file, deps))
    workflow.add_node("upload_parse_and_validate", bind_node(upload_parse_and_validate, deps))
    workflow.add_node("upload_resume_filter", bind_node(upload_resume_filter, deps))
    workflow.add_node("upload_backfill_metadata", bind_node(upload_backfill_metadata, deps))
    workflow.add_node("upload_decide_write_mode", bind_node(upload_decide_write_mode, deps))
    workflow.add_node("upload_persist", bind_node(upload_persist, deps))
    workflow.add_node("prepare_deferred_retry", bind_node(_prepare_deferred_retry, deps))
    workflow.add_node("upload_summarize", bind_node(upload_summarize, deps))

    workflow.add_edge(START, "upload_load_file")
    workflow.add_edge("upload_load_file", "upload_parse_and_validate")
    workflow.add_edge("upload_parse_and_validate", "upload_resume_filter")
    workflow.add_edge("upload_resume_filter", "upload_backfill_metadata")
    workflow.add_edge("upload_backfill_metadata", "upload_decide_write_mode")
    workflow.add_edge("upload_decide_write_mode", "upload_persist")
    workflow.add_conditional_edges(
        "upload_persist",
        _route_after_persist,
        {
            "prepare_deferred_retry": "prepare_deferred_retry",
            "upload_summarize": "upload_summarize",
        },
    )
    workflow.add_edge("prepare_deferred_retry", "upload_decide_write_mode")
    workflow.add_edge("upload_summarize", END)
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
