"""LangGraph workflow:
validate_input -> route_intent -> plan -> execute_tools(-> retry) -> validate_results -> generate_response
-> safety_check -> finalize. Any node can short-circuit to `finalize` (failed / limit_reached)."""
from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.agents.nodes import pipeline as n
from app.agents.state import AgentState

TERMINAL = ("failed", "limit_reached")


def _next(target: str):
    return lambda s: "finalize" if s.get("status") in TERMINAL else target


def _after_execute(s: AgentState) -> str:
    if s.get("status") in TERMINAL:
        return "finalize"
    return "execute_tools" if s.get("needs_retry") else "validate_results"


@lru_cache
def build_graph():
    g = StateGraph(AgentState)
    for name in ("validate_input", "route_intent", "plan", "execute_tools", "validate_results",
                 "generate_response", "safety_check", "finalize"):
        g.add_node(name, getattr(n, name))
    g.set_entry_point("validate_input")
    chain = [("validate_input", "route_intent"), ("route_intent", "plan"), ("plan", "execute_tools"),
             ("validate_results", "generate_response"), ("generate_response", "safety_check"),
             ("safety_check", "finalize")]
    for src, dst in chain:
        g.add_conditional_edges(src, _next(dst), {dst: dst, "finalize": "finalize"})
    g.add_conditional_edges("execute_tools", _after_execute, {"execute_tools": "execute_tools",
                            "validate_results": "validate_results", "finalize": "finalize"})
    g.add_edge("finalize", END)
    return g.compile()
