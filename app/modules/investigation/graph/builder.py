from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from langgraph.graph import END, StateGraph

from app.modules.investigation.graph.state import RunState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver


def _intake(state: RunState) -> dict[str, Any]:
    return {}


def _finalize(state: RunState) -> dict[str, Any]:
    request = state.get("request") or {}
    result_json = {
        "stub": True,
        "profile": request.get("profile"),
        "address": request.get("address"),
        "claims": [],
        "missing_information": ["Investigation pipeline not yet implemented."],
        "uncertainty": [],
        "conflicts": [],
    }
    return {"result_json": result_json}


def build_graph(
    variant: Literal["single", "rules", "llm"],
    *,
    checkpointer: BaseCheckpointSaver | None = None,
):
    _ = variant
    graph = StateGraph(RunState)
    graph.add_node("intake", _intake)
    graph.add_node("finalize", _finalize)
    graph.set_entry_point("intake")
    graph.add_edge("intake", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)
