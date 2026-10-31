from __future__ import annotations

import uuid

from langgraph.checkpoint.memory import MemorySaver

from app.modules.investigation.graph.builder import build_graph


def test_stub_graph_writes_placeholder_result() -> None:
    graph = build_graph("rules", checkpointer=MemorySaver())
    job_id = uuid.uuid4()
    config = {"configurable": {"thread_id": str(job_id)}}
    final = graph.invoke(
        {
            "job_id": str(job_id),
            "request": {"profile": "homebuyer", "address": "Test 1"},
        },
        config=config,
    )
    assert final["result_json"]["stub"] is True
    assert final["result_json"]["profile"] == "homebuyer"
