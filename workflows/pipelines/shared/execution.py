"""Reusable graph execution helpers shared across workflow entry points."""

from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol, cast

from comicbook.deps import Deps

if TYPE_CHECKING:
    from comicbook.state import RunState
else:
    RunState = dict[str, object]


NodeCallable = Callable[[RunState, Deps], dict[str, object]]


class CompiledWorkflow(Protocol):
    def invoke(self, state: RunState) -> RunState: ...


GraphFactory = Callable[[Deps], CompiledWorkflow]


@lru_cache(maxsize=1)
def _load_legacy_state_module() -> object:
    legacy_state_path = Path(__file__).resolve().parents[3] / "ComicBook" / "comicbook" / "state.py"
    module_name = "_legacy_comicbook_state"
    module = sys.modules.get(module_name)
    if module is None:
        spec = importlib.util.spec_from_file_location(module_name, legacy_state_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load legacy state module from {legacy_state_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        sys.modules.setdefault("comicbook.state", module)
        spec.loader.exec_module(module)
    else:
        sys.modules.setdefault("comicbook.state", module)
    return module


@lru_cache(maxsize=1)
def _load_ingest_callable() -> NodeCallable:
    try:
        from comicbook.nodes.ingest import ingest
    except ModuleNotFoundError:
        _load_legacy_state_module()
        legacy_ingest_path = Path(__file__).resolve().parents[3] / "ComicBook" / "comicbook" / "nodes" / "ingest.py"
        module_name = "_legacy_comicbook_nodes_ingest"
        module = sys.modules.get(module_name)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, legacy_ingest_path)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Unable to load legacy ingest module from {legacy_ingest_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        ingest = module.ingest
    return cast(NodeCallable, ingest)


def bind_node(node: NodeCallable, deps: Deps) -> Callable[[RunState], dict[str, object]]:
    """Bind the shared dependency container into a LangGraph node."""

    return lambda state, fn=node: fn(state, deps)


def pid_is_alive(pid: int) -> bool:
    """Return whether the given process id appears to still exist."""

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def format_timestamp(value: datetime) -> str:
    """Render a consistent UTC-ish timestamp string for persisted records."""

    normalized = value.astimezone(timezone.utc) if value.tzinfo is not None else value
    rendered = normalized.replace(microsecond=0).isoformat()
    return rendered.replace("+00:00", "Z") if value.tzinfo is not None else f"{rendered}Z"


def prepare_initial_state(state: RunState, deps: Deps) -> RunState:
    """Normalize caller input before lock acquisition and graph execution."""

    prepared = dict(state)
    prepared.update(_load_ingest_callable()(state, deps))
    return cast(RunState, prepared)


def run_graph_with_lock(initial_state: RunState, deps: Deps, *, graph_factory: GraphFactory) -> RunState:
    """Acquire the run lock, invoke a compiled graph, and finalize crashes safely."""

    prepared_state = prepare_initial_state(initial_state, deps)
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
        pid_is_alive=pid_is_alive,
    )

    graph = graph_factory(deps)
    try:
        return graph.invoke(prepared_state)
    except Exception:
        run_record = deps.db.get_run(run_id)
        if run_record is not None and run_record.status == "running":
            deps.db.finalize_run(
                run_id=run_id,
                ended_at=format_timestamp(deps.clock()),
                status="failed",
                cache_hits=0,
                generated=0,
                failed=0,
                skipped_rate_limit=0,
                est_cost_usd=0.0,
                router_prompt_version=deps.config.comicbook_router_prompt_version,
            )
        raise


__all__ = [
    "CompiledWorkflow",
    "GraphFactory",
    "NodeCallable",
    "bind_node",
    "format_timestamp",
    "pid_is_alive",
    "prepare_initial_state",
    "run_graph_with_lock",
]
