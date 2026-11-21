"""The agent's tool set. Every tool is user-scoped through ctx.user and returns structured data."""
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.repositories.finance import AccountRepo, CategoryRepo, TransactionRepo, TxFilter
from app.repositories.planning import BudgetRepo, GoalRepo
from app.schemas.planning import BudgetIn, BudgetItemIn, GoalIn
from app.services.accounts import AccountService
from app.services.alerts import ALERT_TYPES, AlertService
from app.services.anomaly import AnomalyService
from app.services.budgets import BudgetService
from app.services.finance import FinanceService
from app.services.goals import GoalService
from app.services.insights import InsightService
from app.tools.registry import ToolContext, ToolError, tool
from app.utils.money import q2
from app.utils.periods import add_months, resolve_month

MonthStr = str | None


class MonthArgs(BaseModel):
    month: MonthStr = Field(default=None, pattern=r"^(\d{4}-(0[1-9]|1[0-2])|this_month|last_month)$")


class NoArgs(BaseModel):
    pass


def _category(ctx: ToolContext, name: str):
    repo = CategoryRepo(ctx.db, ctx.user.id)
    exact = repo.get_by_name(name)
    if exact:
        return exact
    needle = name.strip().lower().rstrip("s")
    hits = [c for c in repo.list() if needle and (needle in c.name.lower() or c.name.lower().rstrip("s") in needle)]
    if len(hits) == 1:
        return hits[0]
    raise ToolError("CATEGORY_NOT_FOUND", f"No category matching '{name}'")


# ---- transactions / accounts ---------------------------------------------------------------------
class GetTransactionsArgs(MonthArgs):
    search: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=80)
    direction: Literal["income", "expense"] | None = None
    days: int | None = Field(default=None, ge=1, le=365)
    limit: int = Field(default=10, ge=1, le=20)


@tool("get_transactions", GetTransactionsArgs, "Search the user's transactions (max 20 rows)")
def get_transactions(ctx: ToolContext, a: GetTransactionsArgs) -> dict:
    f = TxFilter(search=a.search, direction=a.direction, currency=ctx.user.currency)
    if a.category:
        f.category_id = _category(ctx, a.category).id
    if a.days:
        f.date_from, f.date_to = ctx.today - timedelta(days=a.days), ctx.today
    elif a.month:
        f.date_from, f.date_to, _ = resolve_month(a.month, ctx.today)
    rows, total = TransactionRepo(ctx.db, ctx.user.id).page(f, a.limit, 0)
    return {"total_matching": total, "returned": len(rows), "_owner_ids": [t.user_id for t in rows],
            "transactions": [{"id": t.id, "date": t.posted_on, "description": t.description,
                              "amount": t.amount, "direction": t.direction,
                              "category": t.category.name if t.category else None} for t in rows]}


class TxIdArgs(BaseModel):
    transaction_id: int = Field(gt=0)


@tool("get_transaction", TxIdArgs, "Get one transaction by id")
def get_transaction(ctx: ToolContext, a: TxIdArgs) -> dict:
    t = TransactionRepo(ctx.db, ctx.user.id).get(a.transaction_id)
    if not t:
        raise ToolError("TRANSACTION_NOT_FOUND", "Transaction not found")
    return {"_owner_ids": [t.user_id], "id": t.id, "date": t.posted_on, "description": t.description,
            "amount": t.amount, "direction": t.direction, "category": t.category.name if t.category else None,
            "anomaly_score": t.anomaly_score}


@tool("get_account_summary", NoArgs, "List accounts with balances")
def get_account_summary(ctx: ToolContext, a: NoArgs) -> dict:
    accounts = AccountRepo(ctx.db, ctx.user.id).list()
    bal = AccountService(ctx.db, ctx.user).balances(accounts)
    by_currency: dict[str, Decimal] = {}
    for acc in accounts:
        by_currency[acc.currency] = by_currency.get(acc.currency, Decimal(0)) + bal[acc.id]
    return {"_owner_ids": [x.user_id for x in accounts],
            "accounts": [{"name": x.name, "type": x.type, "currency": x.currency, "balance": q2(bal[x.id])}
                         for x in accounts],
            "total_by_currency": {k: q2(v) for k, v in by_currency.items()}}


# ---- spending / cash flow --------------------------------------------------------------------------
class SpendingArgs(MonthArgs):
    compare_to_previous: bool = False


@tool("get_spending_summary", SpendingArgs, "Income, spending, top categories (optionally vs previous month)")
def get_spending_summary(ctx: ToolContext, a: SpendingArgs) -> dict:
    first, last, label = resolve_month(a.month, ctx.today)
    fin = FinanceService(ctx.db, ctx.user, ctx.today)
    cf = fin.cashflow(first, last)
    out = {"month": label, "currency": ctx.user.currency, "income": cf.income, "expense": cf.expense,
           "net": cf.net, "expense_count": cf.expense_count,
           "categories": fin.category_spending(first, last)}
    if a.compare_to_previous:
        out["comparison"] = fin.compare_months(first)
    return out


class CategorySpendArgs(MonthArgs):
    category: str = Field(min_length=1, max_length=80)


@tool("get_category_spending", CategorySpendArgs, "Spending in one category for a month")
def get_category_spending(ctx: ToolContext, a: CategorySpendArgs) -> dict:
    cat = _category(ctx, a.category)
    first, last, label = resolve_month(a.month, ctx.today)
    fin = FinanceService(ctx.db, ctx.user, ctx.today)
    rows = fin.category_spending(first, last)
    mine = next((r for r in rows if r["category_id"] == cat.id), None)
    total_expense = fin.cashflow(first, last).expense
    return {"month": label, "category": cat.name, "currency": ctx.user.currency,
            "total": mine["total"] if mine else q2(0), "count": mine["count"] if mine else 0,
            "share_pct": mine["share_pct"] if mine else None, "total_expense": total_expense}


class MonthlyArgs(BaseModel):
    months: int = Field(default=6, ge=1, le=12)


@tool("get_monthly_spending", MonthlyArgs, "Income/expense per month for the last N months")
def get_monthly_spending(ctx: ToolContext, a: MonthlyArgs) -> dict:
    return {"currency": ctx.user.currency,
            "series": FinanceService(ctx.db, ctx.user, ctx.today).monthly_series(a.months)}


@tool("calculate_cashflow", MonthArgs, "Income, expenses and net cash flow for a month")
def calculate_cashflow(ctx: ToolContext, a: MonthArgs) -> dict:
    first, last, label = resolve_month(a.month, ctx.today)
    cf = FinanceService(ctx.db, ctx.user, ctx.today).cashflow(first, last)
    return {"month": label, "currency": ctx.user.currency, "income": cf.income, "expense": cf.expense,
            "net": cf.net}


@tool("calculate_savings_rate", MonthArgs, "Savings rate (%) for a month")
def calculate_savings_rate(ctx: ToolContext, a: MonthArgs) -> dict:
    first, last, label = resolve_month(a.month, ctx.today)
    cf = FinanceService(ctx.db, ctx.user, ctx.today).cashflow(first, last)
    return {"month": label, "currency": ctx.user.currency, "income": cf.income, "expense": cf.expense,
            "net": cf.net, "savings_rate": cf.savings_rate}


class AnomalyArgs(BaseModel):
    days: int = Field(default=90, ge=1, le=365)


@tool("detect_anomalies", AnomalyArgs, "Find unusual expense transactions in the last N days")
def detect_anomalies(ctx: ToolContext, a: AnomalyArgs) -> dict:
    found = AnomalyService(ctx.db, ctx.user, ctx.today).detect(ctx.today - timedelta(days=a.days), ctx.today,
                                                               persist=False)
    return {"days": a.days, "currency": ctx.user.currency, "count": len(found), "unusual": found[:10]}


# ---- budgets ---------------------------------------------------------------------------------------
class NamedBudgetArgs(MonthArgs):
    budget: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=80)


def _budgets(ctx: ToolContext, name: str | None):
    repo = BudgetRepo(ctx.db, ctx.user.id)
    if name:
        b = repo.get_by_name(name)
        if not b:
            raise ToolError("BUDGET_NOT_FOUND", f"No budget named '{name}'")
        return [b]
    return repo.list("active")


@tool("get_budget", NamedBudgetArgs, "List budgets and their limits")
def get_budget(ctx: ToolContext, a: NamedBudgetArgs) -> dict:
    budgets = _budgets(ctx, a.budget)
    return {"_owner_ids": [b.user_id for b in budgets], "currency": ctx.user.currency,
            "budgets": [{"id": b.id, "name": b.name, "status": b.status,
                         "items": [{"category": i.category.name, "limit": q2(i.limit_amount)}
                                   for i in b.items]} for b in budgets]}


@tool("get_budget_status", NamedBudgetArgs, "Actual vs planned spending for budgets")
def get_budget_status(ctx: ToolContext, a: NamedBudgetArgs) -> dict:
    budgets = _budgets(ctx, a.budget)
    svc = BudgetService(ctx.db, ctx.user, ctx.today)
    statuses = [svc.status(b, a.month) for b in budgets]
    if a.category:
        cat = _category(ctx, a.category)
        for s in statuses:
            s["items"] = [i for i in s["items"] if i["category_id"] == cat.id]
        statuses = [s for s in statuses if s["items"]]
    return {"_owner_ids": [b.user_id for b in budgets], "currency": ctx.user.currency, "budgets": statuses}


class BudgetLine(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    limit_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class CreateBudgetArgs(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    items: list[BudgetLine] = Field(min_length=1, max_length=20)


@tool("create_budget", CreateBudgetArgs, "Create a monthly budget", mutating=True)
def create_budget(ctx: ToolContext, a: CreateBudgetArgs) -> dict:
    items = [BudgetItemIn(category_id=_category(ctx, i.category).id, limit_amount=i.limit_amount)
             for i in a.items]
    b = BudgetService(ctx.db, ctx.user, ctx.today).create(BudgetIn(name=a.name, items=items))
    return {"_owner_ids": [b.user_id], "created": True, "budget_id": b.id, "name": b.name,
            "currency": ctx.user.currency,
            "items": [{"category": i.category.name, "limit": q2(i.limit_amount)} for i in b.items]}


class UpdateBudgetArgs(BaseModel):
    budget: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    limit_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


@tool("update_budget", UpdateBudgetArgs, "Set/replace the limit of one category in a budget", mutating=True)
def update_budget(ctx: ToolContext, a: UpdateBudgetArgs) -> dict:
    from app.schemas.planning import BudgetUpdate
    b = _budgets(ctx, a.budget)[0]
    cat = _category(ctx, a.category)
    merged = {i.category_id: i.limit_amount for i in b.items}
    merged[cat.id] = a.limit_amount
    svc = BudgetService(ctx.db, ctx.user, ctx.today)
    b = svc.update(b.id, BudgetUpdate(items=[BudgetItemIn(category_id=k, limit_amount=v)
                                             for k, v in merged.items()]))
    return {"_owner_ids": [b.user_id], "updated": True, "budget_id": b.id, "name": b.name,
            "category": cat.name, "limit": q2(a.limit_amount), "currency": ctx.user.currency}


# ---- goals -----------------------------------------------------------------------------------------
class GoalLookupArgs(BaseModel):
    goal: str | None = Field(default=None, max_length=120)


def _goal_progress(ctx: ToolContext, name: str | None) -> dict:
    svc = GoalService(ctx.db, ctx.user, ctx.today)
    goals = [GoalRepo(ctx.db, ctx.user.id).get_by_name(name)] if name else GoalRepo(ctx.db, ctx.user.id).list()
    if name and goals[0] is None:
        raise ToolError("GOAL_NOT_FOUND", f"No goal named '{name}'")
    avg = FinanceService(ctx.db, ctx.user, ctx.today).average_monthly_net()
    return {"_owner_ids": [g.user_id for g in goals], "currency": ctx.user.currency,
            "goals": [svc.progress(g, avg) for g in goals]}


@tool("get_goals", GoalLookupArgs, "List the user's goals")
def get_goals(ctx: ToolContext, a: GoalLookupArgs) -> dict:
    res = _goal_progress(ctx, a.goal)
    for g in res["goals"]:
        for k in ("avg_monthly_net", "pace", "months_left", "required_monthly"):
            g.pop(k, None)
    return res


@tool("get_goal_progress", GoalLookupArgs, "Goal progress, required monthly saving and pace")
def get_goal_progress(ctx: ToolContext, a: GoalLookupArgs) -> dict:
    return _goal_progress(ctx, a.goal)


class CreateGoalArgs(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    months: int | None = Field(default=None, ge=1, le=600)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)


@tool("create_goal", CreateGoalArgs, "Create a savings goal", mutating=True)
def create_goal(ctx: ToolContext, a: CreateGoalArgs) -> dict:
    deadline = add_months(ctx.today, a.months) if a.months else None
    svc = GoalService(ctx.db, ctx.user, ctx.today)
    g = svc.create(GoalIn(name=a.name, target_amount=a.target_amount, current_amount=a.current_amount,
                          deadline=deadline))
    return {"created": True, **_goal_progress_single(ctx, svc, g)}


def _goal_progress_single(ctx: ToolContext, svc: GoalService, g) -> dict:
    avg = FinanceService(ctx.db, ctx.user, ctx.today).average_monthly_net()
    return {"_owner_ids": [g.user_id], "currency": ctx.user.currency, "goals": [svc.progress(g, avg)]}


# ---- alerts / insights -----------------------------------------------------------------------------
class CreateAlertArgs(BaseModel):
    type: Literal[ALERT_TYPES]  # type: ignore[valid-type]
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=1000)
    severity: Literal["info", "warning", "critical"] = "info"


@tool("create_alert", CreateAlertArgs, "Create an alert for the user", mutating=True)
def create_alert(ctx: ToolContext, a: CreateAlertArgs) -> dict:
    alert = AlertService(ctx.db, ctx.user).create(a.type, a.title, a.message, a.severity,
                                                  f"manual:{uuid.uuid4().hex}")
    return {"_owner_ids": [alert.user_id], "created": True, "alert_id": alert.id, "type": alert.type}


@tool("get_financial_insights", MonthArgs, "Deterministic monthly insight for a month")
def get_financial_insights(ctx: ToolContext, a: MonthArgs) -> dict:
    insight = InsightService(ctx.db, ctx.user, ctx.today).generate(a.month or "last_month")
    if insight is None:
        _, _, label = resolve_month(a.month or "last_month", ctx.today)
        return {"period": label, "available": False}
    return {"_owner_ids": [insight.user_id], "available": True, "period": insight.period,
            "title": insight.title, "body": insight.body, "data": insight.data}


@tool("get_rag_spending_context", MonthArgs, "Retrieve grounded financial RAG context for personalized savings advice")
def get_rag_spending_context(ctx: ToolContext, a: MonthArgs) -> dict:
    first, last, label = resolve_month(a.month or "this_month", ctx.today)
    finance = FinanceService(ctx.db, ctx.user, ctx.today)
    cf = finance.cashflow(first, last)
    cats = finance.category_spending(first, last)

    # Check budget status for any exceeded categories
    budget_svc = BudgetService(ctx.db, ctx.user, ctx.today)
    all_budgets = budget_svc.all_status(a.month or "this_month")
    overages = []
    for b in all_budgets:
        for item in b.get("items", []):
            if item.get("state") == "exceeded":
                overages.append({
                    "category": item["category"],
                    "spent": str(item["spent"]),
                    "limit": str(item["limit"]),
                    "over_by": str(item["spent"] - item["limit"]),
                })

    # Find recent spending anomalies
    anomaly_svc = AnomalyService(ctx.db, ctx.user, ctx.today)
    anomalies = anomaly_svc.detect(ctx.today - timedelta(days=60), ctx.today, persist=False)
    recent_anomalies = [
        {"merchant": an.get("merchant") or "Unknown", "amount": str(an.get("amount")), "date": an.get("date")}
        for an in anomalies[:3]
    ]

    return {
        "_owner_ids": [ctx.user.id],
        "period": label,
        "currency": ctx.user.currency,
        "income": str(cf.income),
        "expense": str(cf.expense),
        "net": str(cf.net),
        "savings_rate_pct": float(cf.savings_rate) if cf.savings_rate is not None else 0.0,
        "top_categories": [
            {"category": x["category"], "total": str(x["total"]), "share_pct": float(x["share_pct"])}
            for x in cats[:5]
        ],
        "budget_overages": overages,
        "recent_anomalies": recent_anomalies,
    }
