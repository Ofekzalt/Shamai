from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from langgraph.graph import END, START, StateGraph

from app.modules.investigation.graph.agents.development import development_node
from app.modules.investigation.graph.agents.market import market_node
from app.modules.investigation.graph.finalize import finalize_node
from app.modules.investigation.graph.intake import intake
from app.modules.investigation.graph.single_agent import single_agent
from app.modules.investigation.graph.state import RunState
from app.modules.investigation.graph.supervisor_llm import route_supervisor_llm
from app.modules.investigation.graph.supervisor_rules import route_after_intake, route_supervisor
from app.modules.investigation.graph.verify import route_after_verify, verify_node
from app.modules.investigation.graph.writer import writer_node

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver

Variant = Literal["single", "rules", "llm"]


def build_graph(
    variant: Variant,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
):
    graph = StateGraph(RunState)
    graph.add_node("intake", intake)
    graph.add_node("writer", writer_node)
    graph.add_node("verify", verify_node)
    graph.add_node("finalize", finalize_node)

    if variant == "single":
        graph.add_node("single", single_agent)
        graph.add_edge(START, "intake")
        graph.add_conditional_edges(
            "intake",
            lambda state: "finalize" if not state.get("geocode_ok") else "single",
            {"finalize": "finalize", "single": "single"},
        )
        graph.add_edge("single", "writer")
    else:
        graph.add_node("market", market_node)
        graph.add_node("development", development_node)
        graph.add_node("supervisor", lambda _state: {})
        graph.add_edge(START, "intake")
        graph.add_conditional_edges("intake", route_after_intake)
        graph.add_edge("market", "supervisor")
        graph.add_edge("development", "supervisor")
        router = route_supervisor_llm if variant == "llm" else route_supervisor
        graph.add_conditional_edges("supervisor", router)
    graph.add_edge("writer", "verify")
    graph.add_conditional_edges("verify", route_after_verify)
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)
