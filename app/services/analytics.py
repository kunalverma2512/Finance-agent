from datetime import date

from sqlalchemy.orm import Session

from app.models import User
from app.repositories.planning import AlertRepo
from app.services.budgets import BudgetService
from app.services.finance import FinanceService
from app.services.goals import GoalService
from app.utils.periods import month_bounds, resolve_month


class AnalyticsService:
    def __init__(self, db: Session, user: User, today: date | None = None) -> None:
        self.db, self.user = db, user
        self.today = today or date.today()
        self.finance = FinanceService(db, user, self.today)

    def summary(self, month: str | None) -> dict:
        first, last, label = resolve_month(month, self.today)
        cf = self.finance.cashflow(first, last)
        goals = GoalService(self.db, self.user, self.today)
        return {
            "month": label, "currency": self.user.currency,
            "cashflow": cf.__dict__,
            "category_spending": self.finance.category_spending(first, last),
            "comparison": self.finance.compare_months(first),
            "monthly_series": self.finance.monthly_series(6, first),
            "budgets": BudgetService(self.db, self.user, self.today).all_status(label),
            "goals": goals.all_progress("active"),
            "recurring": self.finance.recurring(),
            "unread_alerts": AlertRepo(self.db, self.user.id).unread_count(),
        }

    def categories(self, month: str | None) -> list[dict]:
        first, last, _ = resolve_month(month, self.today)
        return self.finance.category_spending(first, last)

    def monthly(self, months: int) -> list[dict]:
        return self.finance.monthly_series(months)


__all__ = ["AnalyticsService", "month_bounds"]
