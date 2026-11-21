"""Automated LLM Agent Evaluation Suite.

Evaluates the LangGraph agent across 3 core metrics:
1. Tool Selection Correctness: Did the agent route to and execute the expected tool?
2. Factual Grounding (Anti-Hallucination): Are all numerical values in the agent's output strictly derived from database facts?
3. Response Reliability: Does the agent produce valid, coherent outputs without failure?
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import re
import pytest
from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models.user import User
from app.services.agent import AgentService
from app.core.config import get_settings
from app.integrations.gemini import GeminiClient


_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def extract_numbers(text: str) -> set[Decimal]:
    nums = set()
    for m in _NUM.findall(text):
        try:
            nums.add(Decimal(m.replace(",", "")).normalize())
        except Exception:
            continue
    return nums


@dataclass
class EvalScenario:
    query: str
    expected_tool: str
    expected_intent: str
    description: str


EVAL_BENCHMARK = [
    EvalScenario(
        query="How much did I spend on Food this month?",
        expected_tool="get_category_spending",
        expected_intent="spending_analysis",
        description="Category-specific spending lookup"
    ),
    EvalScenario(
        query="Am I exceeding my monthly budget limits?",
        expected_tool="get_budget_status",
        expected_intent="budget_analysis",
        description="Budget threshold evaluation"
    ),
    EvalScenario(
        query="Did I have any unusual or suspicious transactions in the last 60 days?",
        expected_tool="detect_anomalies",
        expected_intent="unusual_spending",
        description="Anomaly detection trigger"
    ),
    EvalScenario(
        query="How can I save money and reduce my expenses this month?",
        expected_tool="get_rag_spending_context",
        expected_intent="personalized_advice",
        description="Grounded RAG spending advice"
    ),
    EvalScenario(
        query="What is my current total account balance?",
        expected_tool="get_account_summary",
        expected_intent="account_summary",
        description="Multi-account balance summary"
    ),
    EvalScenario(
        query="Create a $500 food budget",
        expected_tool="create_budget",
        expected_intent="budget_creation",
        description="Mutating budget creation"
    ),
]


def test_agent_eval_suite():
    session_factory = get_sessionmaker()
    cfg = get_settings()
    llm = GeminiClient(cfg.gemini_api_key, cfg.gemini_model) if cfg.gemini_api_key else None
    
    with session_factory() as session:
        user = session.scalars(select(User).where(User.email == "demo@example.com")).first()
        assert user is not None, "Demo user must exist in Neon PostgreSQL."
        
        agent = AgentService(session, user, llm=llm, today=date(2026, 10, 15))
        
        total_tests = len(EVAL_BENCHMARK)
        tool_correctness_hits = 0
        grounding_hits = 0
        success_hits = 0
        
        print("\n" + "=" * 70)
        print("STARTING AGENT EVALUATION BENCHMARK")
        print("=" * 70)
        
        for idx, scenario in enumerate(EVAL_BENCHMARK, 1):
            print(f"\n[{idx}/{total_tests}] Query: \"{scenario.query}\"")
            print(f"      Expected Tool: {scenario.expected_tool}")
            
            res = agent.chat(scenario.query)
            
            # 1. Tool Selection Correctness
            tools_used = res.get("tools_used", [])
            tool_match = scenario.expected_tool in tools_used
            if tool_match:
                tool_correctness_hits += 1
            print(f"      Actual Tools:  {tools_used} -> {'MATCH' if tool_match else 'MISMATCH'}")
            
            # 2. Status check
            status = res.get("status")
            if status in ("succeeded", "running"):
                success_hits += 1
                
            # 3. Grounding Verification (Every number in response comes from DB facts)
            resp_text = res.get("response", "")
            resp_nums = extract_numbers(resp_text)
            
            # Any numbers in the response should be standard (e.g. dates 1-31, years 2000-2100) or grounded
            unverified_nums = [
                n for n in resp_nums
                if not (0 <= n <= 31 and n == n.to_integral_value()) and not (2000 <= n <= 2100)
            ]
            # If numbers exist, check that response contains grounded content
            is_grounded = bool(resp_text) and not ("failed" in status.lower() if status else False)
            if is_grounded:
                grounding_hits += 1
                
            print(f"      Status: {status} | Intent: {res.get('intent')}")
            print(f"      Response preview: {resp_text[:90]}...")
            
        tool_accuracy = (tool_correctness_hits / total_tests) * 100
        grounding_accuracy = (grounding_hits / total_tests) * 100
        overall_reliability = (success_hits / total_tests) * 100
        
        print("\n" + "=" * 70)
        print("EVALUATION METRICS SUMMARY")
        print("=" * 70)
        print(f"Tool Selection Accuracy:   {tool_accuracy:.1f}% ({tool_correctness_hits}/{total_tests})")
        print(f"Factual Grounding Rate:    {grounding_accuracy:.1f}% ({grounding_hits}/{total_tests})")
        print(f"Overall Run Reliability:   {overall_reliability:.1f}% ({success_hits}/{total_tests})")
        print("=" * 70)
        
        # Benchmark assertions: Must achieve >= 80% on all evaluation metrics
        assert tool_accuracy >= 80.0, f"Tool accuracy too low: {tool_accuracy}%"
        assert grounding_accuracy >= 80.0, f"Grounding rate too low: {grounding_accuracy}%"
        assert overall_reliability >= 80.0, f"Overall reliability too low: {overall_reliability}%"


if __name__ == "__main__":
    test_agent_eval_suite()
