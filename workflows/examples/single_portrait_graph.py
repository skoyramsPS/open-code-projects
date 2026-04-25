"""Alternate example graph that reuses the shared workflow modules for one portrait."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from comicbook.deps import Deps
from comicbook.execution import bind_node, run_graph_with_lock
from comicbook.nodes.cache_lookup import cache_lookup
from comicbook.nodes.generate_images_serial import generate_images_serial
from comicbook.nodes.ingest import ingest
from comicbook.nodes.load_templates import load_templates
from comicbook.nodes.persist_template import persist_template
from comicbook.nodes.router import router
from comicbook.nodes.summarize import summarize
from comicbook.state import RunState


def enforce_single_portrait(state: RunState, deps: Deps) -> dict[str, object]:
    """Pin the router-visible request contract to exactly one portrait image."""

    del deps
    return {"exact_image_count": 1}


def build_single_portrait_graph(deps: Deps):
    """Compile an alternate graph that proves the shared modules are reusable."""

    workflow = StateGraph(RunState)
    workflow.add_node("ingest", bind_node(ingest, deps))
    workflow.add_node("enforce_single_portrait", bind_node(enforce_single_portrait, deps))
    workflow.add_node("load_templates", bind_node(load_templates, deps))
    workflow.add_node("router", bind_node(router, deps))
    workflow.add_node("persist_template", bind_node(persist_template, deps))
    workflow.add_node("cache_lookup", bind_node(cache_lookup, deps))
    workflow.add_node("generate_images_serial", bind_node(generate_images_serial, deps))
    workflow.add_node("summarize", bind_node(summarize, deps))

    workflow.add_edge(START, "ingest")
    workflow.add_edge("ingest", "enforce_single_portrait")
    workflow.add_edge("enforce_single_portrait", "load_templates")
    workflow.add_edge("load_templates", "router")
    workflow.add_edge("router", "persist_template")
    workflow.add_edge("persist_template", "cache_lookup")
    workflow.add_edge("cache_lookup", "generate_images_serial")
    workflow.add_edge("generate_images_serial", "summarize")
    workflow.add_edge("summarize", END)
    return workflow.compile()


def run_single_portrait_workflow(initial_state: RunState, deps: Deps) -> RunState:
    """Execute the alternate single-portrait example graph with the shared runtime helper."""

    return run_graph_with_lock(initial_state, deps, graph_factory=build_single_portrait_graph)


__all__ = ["build_single_portrait_graph", "enforce_single_portrait", "run_single_portrait_workflow"]
