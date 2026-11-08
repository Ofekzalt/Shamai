from __future__ import annotations

from typing import Any

from langgraph.types import RunnableConfig

from app.modules.investigation.graph.agents import development as development_agent
from app.modules.investigation.graph.agents import market as market_agent
from app.modules.investigation.graph.runtime import get_runtime, node_session
from app.modules.investigation.graph.specialist import ToolBudget
from app.modules.investigation.graph.state import RunState


def single_agent(state: RunState, config: RunnableConfig) -> dict[str, Any]:
    runtime = get_runtime(config)
    budget = ToolBudget(max_calls=runtime.settings.max_tool_calls, agent="single")
    with node_session(runtime) as session:
        market_findings, _ = market_agent._first_pass(state, runtime, session, budget)
        development_findings: dict[str, Any] = {}
        conflicts: list[str] = []
        if budget.remaining() > 0:
            development_findings, _queued, conflicts = development_agent._first_pass(
                state, runtime, session, budget
            )
        return {
            "agent_results": [
                {"agent": "market", "findings": market_findings},
                {"agent": "development", "findings": development_findings},
            ],
            "followup_queue": [],
            "conflicts": conflicts,
            "tool_calls": budget.calls,
            "dispatches_used": 1,
        }
