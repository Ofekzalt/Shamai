from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from app.modules.investigation.graph.builder import build_graph


def test_all_variants_compile() -> None:
    checkpointer = MemorySaver()
    for variant in ("single", "rules", "llm"):
        graph = build_graph(variant, checkpointer=checkpointer)
        assert graph is not None
