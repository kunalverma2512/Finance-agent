"""Deterministic finance engine. The LLM never computes any of these numbers."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median

from sqlalchemy.orm import Session

from app.models import User
from app.repositories.finance import TransactionRepo
from app.utils.money import ZERO, pct, q2
from app.utils.periods import label, month_bounds, shift_month


# ---- pure functions (unit-testable without a database) ----------------------------------------
def net_cashflow(income: Decimal, expense: Decimal) -> Decimal:
    return q2(income - expense)


def savings_rate(income: Decimal, expense: Decimal) -> Decimal | None:
    """(income - expense) / income * 100, or None when there is no income."""
    return pct(income - expense, income)


def pct_change(current: Decimal, previous: Decimal) -> Decimal | None:
    return pct(current - previous, previous)


def detect_recurring(rows: list[tuple[date, Decimal, str]], min_months: int = 3,
                     tolerance: Decimal = Decimal("0.15")) -> list[dict]:
    """Merchants charged in >= min_months distinct months with a stable amount."""
    by_merchant: dict[str, list[tuple[date, Decimal]]] = defaultdict(list)
    for d, amount, merchant in rows:
        if merchant:
            by_merchant[merchant].append((d, amount))
    out = []
    for merchant, items in by_merchant.items():
        months = {label(d) for d, _ in items}
        amounts = [a for _, a in items]
        typical = median(amounts)
        if len(months) >= min_months and all(abs(a - typical) <= typical * tolerance for a in amounts):
            out.append({"merchant": merchant, "typical_amount": q2(typical), "months_seen": len(months)})
    return sorted(out, key=lambda r: r["typical_amount"], reverse=True)


@dataclass
class Cashflow:
    income: Decimal
    expense: Decimal
    net: Decimal
    savings_rate: Decimal | None
    income_count: int
    expense_count: int
    average_expense: Decimal | None


class FinanceService:
    def __init__(self, db: Session, user: User, today: date | None = None) -> None:
        self.user = user
        self.repo = TransactionRepo(db, user.id)
        self.today = today or date.today()

    def cashflow(self, start: date, end: date, currency: str | None = None) -> Cashflow:
        totals = self.repo.totals(start, end, currency or self.user.currency)
        income, income_n = totals["income"]
        expense, expense_n = totals["expense"]
        return Cashflow(income=q2(income), expense=q2(expense), net=net_cashflow(income, expense),
                        savings_rate=savings_rate(income, expense), income_count=income_n,
                        expense_count=expense_n,
                        average_expense=q2(expense / expense_n) if expense_n else None)

    def category_spending(self, start: date, end: date, currency: str | None = None) -> list[dict]:
        rows = self.repo.by_category(start, end, currency or self.user.currency)
        total = sum((r[2] for r in rows), Decimal("0"))
        return [{"category_id": cid, "category": name, "total": q2(amount), "count": count,
                 "share_pct": pct(amount, total)} for cid, name, amount, count in rows]

    def monthly_series(self, months: int, end_month_first: date | None = None,
                       currency: str | None = None) -> list[dict]:
        end_first = end_month_first or self.today.replace(day=1)
        start_first = shift_month(end_first, -(months - 1))
        data: dict[str, dict[str, Decimal]] = {}
        for i in range(months):
            data[label(shift_month(start_first, i))] = {"income": ZERO, "expense": ZERO}
        rows = self.repo.monthly(start_first, month_bounds(end_first.year, end_first.month)[1],
                                 currency or self.user.currency)
        for month, direction, total in rows:
            data[month][direction] = q2(total)
        return [{"month": m, "income": v["income"], "expense": v["expense"],
                 "net": net_cashflow(v["income"], v["expense"])} for m, v in data.items()]

    def compare_months(self, current_first: date, currency: str | None = None) -> dict:
        prev_first = shift_month(current_first, -1)
        cur = self.cashflow(*month_bounds(current_first.year, current_first.month), currency)
        prev = self.cashflow(*month_bounds(prev_first.year, prev_first.month), currency)
        cur_cat = {c["category"]: c["total"] for c in
                   self.category_spending(*month_bounds(current_first.year, current_first.month), currency)}
        prev_cat = {c["category"]: c["total"] for c in
                    self.category_spending(*month_bounds(prev_first.year, prev_first.month), currency)}
        changes = []
        for name in set(cur_cat) | set(prev_cat):
            c, p = cur_cat.get(name, ZERO), prev_cat.get(name, ZERO)
            changes.append({"category": name, "current": c, "previous": p, "difference": q2(c - p)})
        changes.sort(key=lambda r: abs(r["difference"]), reverse=True)
        return {"current_month": label(current_first), "previous_month": label(prev_first),
                "current_spending": cur.expense, "previous_spending": prev.expense,
                "difference": q2(cur.expense - prev.expense),
                "pct_change": pct_change(cur.expense, prev.expense), "category_changes": changes}

    def recurring(self, months: int = 4, currency: str | None = None) -> list[dict]:
        start = shift_month(self.today.replace(day=1), -(months - 1))
        rows = self.repo.expense_rows_since(start, currency or self.user.currency)
        return detect_recurring([(d, a, m) for _, d, a, _, m in rows])

    def average_monthly_net(self, months: int = 3) -> Decimal | None:
        """Mean net cash flow over the last COMPLETED months that contain any transactions."""
        end_first = shift_month(self.today.replace(day=1), -1)
        series = [m for m in self.monthly_series(months, end_first) if m["income"] or m["expense"]]
        if not series:
            return None
        return q2(sum((m["net"] for m in series), Decimal("0")) / len(series))
