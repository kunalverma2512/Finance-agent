from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Insight, User
from app.repositories.planning import InsightRepo
from app.services.finance import FinanceService
from app.utils.periods import month_bounds, resolve_month, shift_month

KIND = "MONTHLY"


def _m(currency: str, amount: Decimal) -> str:
    return f"{currency} {amount:,.2f}"


class InsightService:
    def __init__(self, db: Session, user: User, today: date | None = None) -> None:
        self.db, self.user = db, user
        self.today = today or date.today()
        self.repo = InsightRepo(db, user.id)
        self.finance = FinanceService(db, user, self.today)

    def generate(self, month: str | None) -> Insight | None:
        """Build (or refresh) the deterministic monthly insight. None when the month has no data."""
        first, last, label = resolve_month(month, self.today)
        cur = self.finance.cashflow(first, last)
        if cur.income_count + cur.expense_count == 0:
            return None
        c = self.user.currency
        cats = self.finance.category_spending(first, last)
        cmp_ = self.finance.compare_months(first)
        lines = [f"In {label} you earned {_m(c, cur.income)} and spent {_m(c, cur.expense)} "
                 f"(net {_m(c, cur.net)})."]
        if cur.savings_rate is not None:
            lines.append(f"Your savings rate was {cur.savings_rate}%.")
        if cats:
            top = cats[0]
            lines.append(f"Biggest spending category: {top['category']} ({_m(c, top['total'])}, "
                         f"{top['share_pct']}% of spending).")
        if cmp_["previous_spending"] > 0:
            direction = "rose" if cmp_["difference"] > 0 else "fell"
            lines.append(f"Spending {direction} by {_m(c, abs(cmp_['difference']))} "
                         f"({abs(cmp_['pct_change'])}%) versus {cmp_['previous_month']}.")
        data = {"income": str(cur.income), "expense": str(cur.expense), "net": str(cur.net),
                "savings_rate": None if cur.savings_rate is None else str(cur.savings_rate),
                "top_categories": [{"category": x["category"], "total": str(x["total"])} for x in cats[:3]]}
        insight = self.repo.upsert(KIND, label, f"Your {label} summary", " ".join(lines), data)
        self.db.commit()
        return insight

    def previous_month_label(self) -> str:
        first = shift_month(self.today.replace(day=1), -1)
        return f"{first.year:04d}-{first.month:02d}"

    def has_data(self, month_label: str) -> bool:
        first, last, _ = resolve_month(month_label, self.today)
        cf = self.finance.cashflow(first, last)
        return bool(cf.income_count + cf.expense_count)

    def list(self, limit: int = 12) -> list[Insight]:
        return self.repo.list(limit)


__all__ = ["InsightService", "month_bounds"]
