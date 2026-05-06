from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from omnisight.graph.nodes import (
    build_evidence_node,
    error_router,
    format_output_node,
    reason_node,
)
from omnisight.graph.state import OmniSightGraphState


def build_omnisight_graph():
    workflow = StateGraph(OmniSightGraphState)

    workflow.add_node("build_evidence", build_evidence_node)
    workflow.add_node("reason_about_product", reason_node)
    workflow.add_node("format_output", format_output_node)

    workflow.add_edge(START, "build_evidence")
    workflow.add_conditional_edges(
        "build_evidence",
        error_router,
        {
            "reason_about_product": "reason_about_product",
            "format_output": "format_output",
        },
    )
    workflow.add_edge("reason_about_product", "format_output")
    workflow.add_edge("format_output", END)

    graph = workflow.compile(checkpointer=InMemorySaver())
    return graph