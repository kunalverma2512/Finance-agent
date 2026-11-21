from typing import Any, TypedDict

INTENTS = ("spending_analysis", "budget_analysis", "budget_creation", "goal_analysis", "transaction_search",
           "unusual_spending", "account_summary", "financial_insight", "personalized_advice", "general_finance_question")


class AgentState(TypedDict, total=False):
    run_id: str
    message: str
    intent: str
    entities: dict[str, Any]
    restricted: bool
    clarification: str
    plan: list[dict[str, Any]]
    done: list[str]            # tool call keys already executed
    results: list[dict[str, Any]]  # {tool, ok, data|error_code, duration_ms}
    tool_calls: int
    retries: int
    needs_retry: bool
    steps: int
    status: str                # running | succeeded | failed | limit_reached
    error: str
    facts: dict[str, Any]
    draft: str
    response: str
    response_source: str       # deterministic | llm | guard_fallback
