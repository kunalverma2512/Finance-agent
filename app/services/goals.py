from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models import FinancialGoal, User
from app.repositories.planning import GoalRepo
from app.schemas.planning import GoalIn, GoalUpdate
from app.services.audit import audit
from app.services.finance import FinanceService
from app.utils.money import ZERO, pct, q2, q2_ceil


def months_until(deadline: date, today: date) -> int | None:
    """Calendar months remaining, a started month counts as a full one (min 1); None if passed."""
    if deadline <= today:
        return None
    months = (deadline.year - today.year) * 12 + deadline.month - today.month
    if deadline.day > today.day:
        months += 1
    return max(1, months)


def required_monthly(remaining: Decimal, months: int) -> Decimal:
    return q2_ceil(remaining / months)


class GoalService:
    def __init__(self, db: Session, user: User, today: date | None = None) -> None:
        self.db, self.user = db, user
        self.today = today or date.today()
        self.repo = GoalRepo(db, user.id)

    def get(self, goal_id: int) -> FinancialGoal:
        g = self.repo.get(goal_id)
        if not g:
            raise NotFoundError("Goal not found", code="GOAL_NOT_FOUND")
        return g

    def create(self, data: GoalIn) -> FinancialGoal:
        if self.repo.get_by_name(data.name):
            raise ConflictError("A goal with this name already exists", code="GOAL_EXISTS")
        if data.deadline and data.deadline <= self.today:
            raise ValidationFailedError("Deadline must be in the future", code="INVALID_DEADLINE")
        goal = self.repo.add(FinancialGoal(name=data.name.strip(), target_amount=data.target_amount,
                                           current_amount=data.current_amount, deadline=data.deadline))
        self._sync_status(goal)
        audit(self.db, self.user.id, "goal.create", "goal", goal.id)
        self.db.commit()
        return goal

    def update(self, goal_id: int, data: GoalUpdate) -> FinancialGoal:
        goal = self.get(goal_id)
        fields = data.model_fields_set
        if data.name and data.name.lower() != goal.name.lower():
            if self.repo.get_by_name(data.name):
                raise ConflictError("A goal with this name already exists", code="GOAL_EXISTS")
            goal.name = data.name.strip()
        if data.target_amount is not None:
            goal.target_amount = data.target_amount
        if "deadline" in fields:
            goal.deadline = data.deadline
        if data.status:
            goal.status = data.status
        self._sync_status(goal)
        self.db.commit()
        return goal

    def contribute(self, goal_id: int, amount: Decimal) -> FinancialGoal:
        goal = self.get(goal_id)
        if goal.status == "archived":
            raise ValidationFailedError("Goal is archived", code="GOAL_ARCHIVED")
        goal.current_amount = goal.current_amount + amount
        self._sync_status(goal)
        audit(self.db, self.user.id, "goal.contribute", "goal", goal.id)
        self.db.commit()
        return goal

    def delete(self, goal_id: int) -> None:
        self.repo.delete(self.get(goal_id))
        self.db.commit()

    @staticmethod
    def _sync_status(goal: FinancialGoal) -> None:
        if goal.status == "archived":
            return
        goal.status = "completed" if goal.current_amount >= goal.target_amount else "active"

    def progress(self, goal: FinancialGoal, avg_monthly_net: Decimal | None = None) -> dict:
        remaining = max(q2(goal.target_amount - goal.current_amount), ZERO)
        out = {"goal_id": goal.id, "name": goal.name, "target": q2(goal.target_amount),
               "current": q2(goal.current_amount), "remaining": remaining,
               "progress_pct": min(pct(goal.current_amount, goal.target_amount) or ZERO, Decimal("100.00")),
               "deadline": goal.deadline, "status": goal.status, "months_left": None,
               "required_monthly": None, "avg_monthly_net": avg_monthly_net, "pace": "no_deadline"}
        if goal.status == "completed":
            out["pace"] = "completed"
        elif goal.deadline:
            months = months_until(goal.deadline, self.today)
            if months is None:
                out["pace"] = "overdue"
            else:
                req = required_monthly(remaining, months)
                out.update(months_left=months, required_monthly=req)
                if avg_monthly_net is None:
                    out["pace"] = "unknown"
                else:
                    out["pace"] = "on_track" if avg_monthly_net >= req else "behind"
        return out

    def all_progress(self, status: str | None = None) -> list[dict]:
        avg = FinanceService(self.db, self.user, self.today).average_monthly_net()
        return [self.progress(g, avg) for g in self.repo.list(status)]

    def all_progress_one(self, goal_id: int) -> dict:
        goal = self.get(goal_id)
        avg = FinanceService(self.db, self.user, self.today).average_monthly_net()
        return self.progress(goal, avg)
