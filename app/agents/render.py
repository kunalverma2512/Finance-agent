"""Deterministic response rendering from VERIFIED tool facts. Every number comes from the backend."""
from decimal import Decimal


def money(cur: str, value: str | Decimal | None) -> str:
    return "n/a" if value is None else f"{cur} {Decimal(str(value)):,.2f}"


def signed(cur: str, value: str) -> str:
    d = Decimal(value)
    return f"{'+' if d > 0 else '-' if d < 0 else ''}{cur} {abs(d):,.2f}"


def _spct(v: str | None) -> str:
    if v is None:
        return "n/a"
    d = Decimal(v)
    return f"{'+' if d > 0 else ''}{d:,.2f}%"


def _pct(v: str | None) -> str:
    return "n/a" if v is None else f"{Decimal(v):,.2f}%"


def render(intent: str, facts: dict[str, dict], cur: str) -> str:
    fn = _RENDERERS.get(intent)
    if not fn:
        return ""
    try:
        return fn(facts, cur)
    except KeyError:  # a planned tool did not run (e.g. tool-call cap) - degrade, never crash
        return "I could only gather part of the data needed for a complete answer. Please try a narrower question."


def _spending(f: dict, cur: str) -> str:
    if "get_category_spending" in f:
        d = f["get_category_spending"]
        if d["count"] == 0:
            return f"I found no {d['category']} spending in {d['month']}."
        return (f"You spent {money(cur, d['total'])} on {d['category']} in {d['month']} "
                f"({d['count']} transactions, {_pct(d['share_pct'])} of your total spending of "
                f"{money(cur, d['total_expense'])}).")
    d = f["get_spending_summary"]
    if d["expense_count"] == 0 and "comparison" not in d:
        return f"I found no expenses recorded for {d['month']}."
    lines = []
    if "comparison" in d:
        c = d["comparison"]
        lines += [f"Current spending ({c['current_month']}): {money(cur, c['current_spending'])}",
                  f"Previous spending ({c['previous_month']}): {money(cur, c['previous_spending'])}",
                  f"Difference: {signed(cur, c['difference'])} ({_spct(c['pct_change'])})"]
        movers = [x for x in c["category_changes"] if Decimal(x["difference"]) != 0][:3]
        if movers:
            lines.append("Top reasons:")
            lines += [f"- {x['category']}: {signed(cur, x['difference'])} "
                      f"({money(cur, x['current'])} vs {money(cur, x['previous'])})" for x in movers]
        lines.append("Suggested actions:")
        if Decimal(c["difference"]) > 0 and movers and Decimal(movers[0]["difference"]) > 0:
            lines.append(f"- Review your {movers[0]['category']} transactions and consider setting a budget for it.")
        else:
            lines.append("- Your spending did not rise; keep tracking it against your budgets.")
    else:
        lines.append(f"In {d['month']} you spent {money(cur, d['expense'])} across {d['expense_count']} "
                     f"transactions and earned {money(cur, d['income'])} (net {signed(cur, d['net'])}).")
        if d["categories"]:
            lines.append("Top categories: " + "; ".join(
                f"{c['category']} {money(cur, c['total'])} ({_pct(c['share_pct'])})" for c in d["categories"][:3]))
    return "\n".join(lines)


def _budget_analysis(f: dict, cur: str) -> str:
    d = f["get_budget_status"]
    if not d["budgets"]:
        return "I couldn't find a matching active budget. You can create one, e.g. \"Create a $500 food budget\"."
    lines = []
    for b in d["budgets"]:
        for i in b["items"]:
            lines.append(f"- {i['category']} ({b['name']}, {b['month']}): spent {money(cur, i['spent'])} of "
                         f"{money(cur, i['limit'])} - {_pct(i['used_pct'])} used, "
                         f"{money(cur, i['remaining'])} remaining [{i['state']}]")
    return "Budget status:\n" + "\n".join(lines)


def _budget_creation(f: dict, cur: str) -> str:
    d = f["create_budget"]
    items = ", ".join(f"{i['category']} {money(cur, i['limit'])}" for i in d["items"])
    return f"Created budget '{d['name']}' with a monthly limit of {items}."


def _goals(f: dict, cur: str) -> str:
    if "create_goal" in f:
        g = f["create_goal"]["goals"][0]
        extra = (f" You would need to save about {money(cur, g['required_monthly'])} per month "
                 f"for {g['months_left']} month(s)." if g.get("required_monthly") else "")
        return f"Created goal '{g['name']}' with a target of {money(cur, g['target'])}.{extra}"
    goals = f["get_goal_progress"]["goals"]
    if not goals:
        return "You have no goals yet. Try: \"Create a goal to save $1500 for a laptop in 6 months\"."
    out = []
    for g in goals:
        line = (f"- {g['name']}: {money(cur, g['current'])} of {money(cur, g['target'])} "
                f"({_pct(g['progress_pct'])}), {money(cur, g['remaining'])} to go")
        if g["required_monthly"] is not None:
            line += (f"; save about {money(cur, g['required_monthly'])}/month for {g['months_left']} month(s)")
        line += f" [{g['pace'].replace('_', ' ')}]"
        out.append(line)
    return "Goal progress:\n" + "\n".join(out)


def _transactions(f: dict, cur: str) -> str:
    d = f["get_transactions"]
    if not d["transactions"]:
        return "I found no matching transactions."
    rows = [f"- {t['date']}  {'+' if t['direction'] == 'income' else '-'}{money(cur, t['amount'])}  "
            f"{t['description']}  ({t['category'] or 'Uncategorized'})" for t in d["transactions"]]
    return f"Showing {d['returned']} of {d['total_matching']} matching transactions:\n" + "\n".join(rows)


def _unusual(f: dict, cur: str) -> str:
    d = f["detect_anomalies"]
    if d["count"] == 0:
        return f"I found no unusual transactions in the last {d['days']} days."
    rows = [f"- {u['date']}  {money(cur, u['amount'])}  {u['merchant'] or 'transaction'}: {u['reason']}"
            for u in d["unusual"][:5]]
    return f"I found {d['count']} unusual transaction(s) in the last {d['days']} days:\n" + "\n".join(rows)


def _accounts(f: dict, cur: str) -> str:
    d = f["get_account_summary"]
    if not d["accounts"]:
        return "You have no accounts yet. Add an account and import a CSV to get started."
    lines = [f"- {a['name']} ({a['type']}): {money(a['currency'], a['balance'])}" for a in d["accounts"]]
    lines += [f"Total ({c}): {money(c, v)}" for c, v in d["total_by_currency"].items()]
    return "Your accounts (balance = opening balance + imported/recorded transactions):\n" + "\n".join(lines)


def _insight(f: dict, cur: str) -> str:
    ins, sr = f["get_financial_insights"], f.get("calculate_savings_rate")
    if not ins.get("available"):
        extra = f" Savings rate: {_pct(sr['savings_rate'])}." if sr else ""
        return f"There is not enough data for {ins['period']} to generate an insight.{extra}"
    return ins["body"]


def _rag_advice(f: dict, cur: str) -> str:
    d = f.get("get_rag_spending_context")
    if not d:
        return "No financial data available to generate personalized advice."
    lines = [f"Financial overview for {d['period']}: Total income {money(cur, d['income'])} and spending {money(cur, d['expense'])} (net {signed(cur, d['net'])})."]
    if d.get("savings_rate_pct"):
        lines.append(f"Current savings rate: {d['savings_rate_pct']:.1f}%.")
    if d.get("top_categories"):
        top = d["top_categories"][0]
        lines.append(f"Your highest spending area is {top['category']} at {money(cur, top['total'])} ({top['share_pct']:.1f}% of total spending).")
    if d.get("budget_overages"):
        lines.append("Budget alerts:")
        for b in d["budget_overages"]:
            lines.append(f"- {b['category']}: spent {money(cur, b['spent'])}, exceeding your limit of {money(cur, b['limit'])} by {money(cur, b['over_by'])}.")
    if d.get("recent_anomalies"):
        lines.append("Unusual charges to review:")
        for a in d["recent_anomalies"]:
            lines.append(f"- {a['merchant']} ({money(cur, a['amount'])}) on {a['date']}")
    top_cat = d['top_categories'][0]['category'] if d.get('top_categories') else 'discretionary'
    lines.append(f"Personalized recommendation:\n- Target a 15% reduction in {top_cat} spending this month to increase your net savings.")
    return "\n".join(lines)


_RENDERERS = {"spending_analysis": _spending, "budget_analysis": _budget_analysis,
              "budget_creation": _budget_creation, "goal_analysis": _goals,
              "transaction_search": _transactions, "unusual_spending": _unusual,
              "account_summary": _accounts, "financial_insight": _insight,
              "personalized_advice": _rag_advice}

RESTRICTED_REPLY = ("I can't move money, give investment, loan, insurance or tax decisions, or promise financial "
                    "outcomes. I can help you understand your spending, budgets and savings goals instead.")
GENERAL_FALLBACK = ("I can help with your spending, budgets, goals, unusual transactions and account summaries. "
                    "Try: \"How much did I spend this month?\" or \"Am I close to my food budget?\"")
GENERAL_DISCLAIMER = "\n\n(General educational information, not personalised financial advice.)"
LIMIT_REPLY = "I stopped because this request needed too many steps. Please try a simpler question."
FAILURE_REPLY = "Sorry, I couldn't complete that request safely. Please try again or rephrase."
