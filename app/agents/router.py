"""Intent routing, entity extraction and planning. Deterministic first; the LLM is only a classifier fallback."""
import re
from datetime import date
from decimal import Decimal

from app.agents.state import INTENTS

MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
}

RESTRICTED = re.compile(
    r"\b(transfer|wire|send|move|pay)\b.*(\bmoney\b|\bfunds\b|\$\s?\d|\b\d+\s?(usd|dollars)\b)"
    r"|\b(should i (buy|sell|invest)|which (stock|crypto)|invest (in|my)|loan (approval|application)|"
    r"approve (a|my) loan|file my taxes?|tax return|guaranteed (return|profit)|insurance underwriting)\b", re.I)
INJECTION = re.compile(r"ignore (all |your )?(previous|prior) instructions|reveal (your )?(system )?prompt|"
                       r"api key|jwt secret|drop table|;\s*select ", re.I)

_AMOUNT = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)|(\d[\d,]*(?:\.\d+)?)\s*(?:dollars|usd)\b", re.I)
_MONTHS = re.compile(r"(\d{1,3})\s*months?", re.I)
_DAYS = re.compile(r"last\s+(\d{1,3})\s+days", re.I)
_YM = re.compile(r"\b(\d{4}-(?:0[1-9]|1[0-2]))\b")
_GOAL_NAME = re.compile(r"\bfor\s+(?:a|an|the|my)?\s*([a-z][a-z0-9 ]{1,40}?)(?:\s+(?:in|by|within|over)\b|[?.!,]|$)", re.I)


def extract_amount(text: str) -> Decimal | None:
    m = _AMOUNT.search(text)
    if not m:
        return None
    return Decimal((m.group(1) or m.group(2)).replace(",", ""))


def extract_period(text: str) -> str:
    t = text.lower()
    if (m := _YM.search(t)):
        return m.group(1)
    current_year = date.today().year
    for m_name, m_num in MONTH_MAP.items():
        if re.search(r"\b" + m_name + r"\b", t):
            return f"{current_year:04d}-{m_num:02d}"
    return "last_month" if "last month" in t or "previous month" in t else "this_month"


def match_category(text: str, names: list[str]) -> str | None:
    t = text.lower()
    words = set(re.findall(r"[a-z]+", t))
    best: tuple[int, str] | None = None
    for name in names:
        low = name.lower()
        score = 0
        if low in t:
            score = len(low) + 10
        else:
            for tok in re.findall(r"[a-z]+", low):
                if len(tok) > 3 and (tok in words or tok.rstrip("s") in words or tok + "s" in words):
                    score = max(score, len(tok))
        if score and (best is None or score > best[0]):
            best = (score, name)
    return best[1] if best else None


def classify(text: str, category_names: list[str]) -> tuple[str | None, dict]:
    """Rule-based intent + entities. Returns (None, entities) when no rule matches."""
    t = text.lower()
    ent: dict = {"month": extract_period(t), "category": match_category(t, category_names),
                 "amount": extract_amount(t)}
    if (m := _DAYS.search(t)):
        ent["days"] = int(m.group(1))
    if (m := _MONTHS.search(t)):
        ent["months"] = int(m.group(1))
    has_create = bool(re.search(r"\b(create|make|set up|set|add|start|open|new)\b", t))
    if has_create and "budget" in t:
        return "budget_creation", ent
    if (has_create and "goal" in t) or re.search(r"\bsave \$?\d[\d,]*.*\bfor\b", t):
        ent["create_goal"] = True
        if (m := _GOAL_NAME.search(text)):
            ent["goal_name"] = m.group(1).strip().title()
        return "goal_analysis", ent
    if re.search(r"unusual|anomal|suspicious|strange|weird|outlier|looks? off|odd (transaction|charge)", t):
        return "unusual_spending", ent
    if "budget" in t:
        return "budget_analysis", ent
    if re.search(r"\bgoals?\b|saving for|save for|need to save", t):
        return "goal_analysis", ent
    if re.search(r"balance|my accounts?|account summary", t):
        return "account_summary", ent
    if re.search(r"transactions?|purchases?|biggest|largest|\bfind\b|\bsearch\b", t):
        return "transaction_search", ent
    if re.search(r"how (can|do) i (save|cut|reduce|spend less)|save more|financial advice|savings tips|where (is|did) my money (go|going)|reduce (expenses?|spending)", t):
        return "personalized_advice", ent
    if re.search(r"insight|overview|report|how am i doing|savings rate|cash ?flow|summary of my", t):
        return "financial_insight", ent
    if re.search(r"spen[dt]|spending|expenses?|costs?", t):
        return "spending_analysis", ent
    if re.match(r"\s*(what is|what's|what are|explain|define|how does|how do|tell me about|"
                r"difference between)\b", t):
        return "general_finance_question", ent  # educational question: no user data, no classifier call
    return None, ent


COMPARE_WORDS = re.compile(r"why|increase|more|less|decrease|compare|change|higher|lower|than|went up|went down")


def build_plan(intent: str, ent: dict, text: str) -> tuple[list[dict], str | None]:
    """(plan, clarification). A plan is an ordered list of {tool, args}."""
    month, cat = ent.get("month"), ent.get("category")
    if intent == "spending_analysis":
        if cat:
            return [{"tool": "get_category_spending", "args": {"category": cat, "month": month}}], None
        return [{"tool": "get_spending_summary",
                 "args": {"month": month, "compare_to_previous": bool(COMPARE_WORDS.search(text.lower()))}}], None
    if intent == "budget_analysis":
        args = {"month": month}
        if cat:
            args["category"] = cat
        return [{"tool": "get_budget_status", "args": args}], None
    if intent == "budget_creation":
        if not cat or ent.get("amount") is None:
            return [], ("To create a budget I need both a category and a monthly limit, for example: "
                        "\"Create a $500 food budget\".")
        return [{"tool": "create_budget", "args": {"name": f"{cat} Budget",
                                                   "items": [{"category": cat,
                                                              "limit_amount": str(ent["amount"])}]}}], None
    if intent == "goal_analysis":
        if ent.get("create_goal"):
            if ent.get("amount") is None or not ent.get("goal_name"):
                return [], ("To create a goal I need a name and a target amount, for example: "
                            "\"Create a goal to save $1500 for a laptop in 6 months\".")
            args = {"name": ent["goal_name"], "target_amount": str(ent["amount"])}
            if ent.get("months"):
                args["months"] = ent["months"]
            return [{"tool": "create_goal", "args": args}], None
        return [{"tool": "get_goal_progress", "args": {}}], None
    if intent == "transaction_search":
        args: dict = {"limit": 10}
        if cat:
            args["category"] = cat
        if ent.get("days"):
            args["days"] = ent["days"]
        elif "last month" in text.lower() or "this month" in text.lower() or ent["month"] != "this_month":
            args["month"] = month
        if re.search(r"\b(biggest|largest)\b", text.lower()):
            args["direction"] = "expense"
        return [{"tool": "get_transactions", "args": args}], None
    if intent == "unusual_spending":
        return [{"tool": "detect_anomalies", "args": {"days": ent.get("days", 90)}}], None
    if intent == "account_summary":
        return [{"tool": "get_account_summary", "args": {}}], None
    if intent == "financial_insight":
        return [{"tool": "get_financial_insights", "args": {"month": month}},
                {"tool": "calculate_savings_rate", "args": {"month": month}}], None
    if intent == "personalized_advice":
        return [{"tool": "get_rag_spending_context", "args": {"month": month}}], None
    return [], None


def valid_intent(value: object) -> str | None:
    return value if isinstance(value, str) and value in INTENTS else None
