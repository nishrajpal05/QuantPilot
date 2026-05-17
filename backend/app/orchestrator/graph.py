from langgraph.graph import StateGraph, END
from app.orchestrator.state import AgentState
from app.orchestrator.nodes import (
    data_node,
    strategy_node,
    backtest_node,
    risk_node,
    compliance_node,
    audit_node,
)


def _should_continue(state: AgentState) -> str:
    """Route to END if error set, otherwise continue."""
    return END if state.get("error") else "continue"


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    # Register nodes
    g.add_node("data",       data_node)
    g.add_node("strategy",   strategy_node)
    g.add_node("backtest",   backtest_node)
    g.add_node("risk",       risk_node)
    g.add_node("compliance", compliance_node)
    g.add_node("audit",      audit_node)

    # Entry
    g.set_entry_point("data")

    # Conditional edges — short-circuit on error after data + strategy + backtest
    g.add_conditional_edges("data",     _should_continue, {"continue": "strategy",   END: END})
    g.add_conditional_edges("strategy", _should_continue, {"continue": "backtest",   END: END})
    g.add_conditional_edges("backtest", _should_continue, {"continue": "risk",       END: END})

    # Risk, compliance, audit are best-effort — always continue even on soft failure
    g.add_edge("risk",       "compliance")
    g.add_edge("compliance", "audit")
    g.add_edge("audit",      END)

    return g.compile()


# Singleton — import and call graph.invoke() from backtest route
graph = build_graph()
