from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models import Budget, BudgetItem, User
from app.repositories.finance import CategoryRepo, TransactionRepo
from app.repositories.planning import BudgetRepo
from app.schemas.planning import BudgetIn, BudgetItemIn, BudgetUpdate
from app.services.audit import audit
from app.utils.money import ZERO, pct, q2
from app.utils.periods import resolve_month

WARNING_PCT = Decimal("80")


def usage_state(spent: Decimal, limit: Decimal) -> str:
    """exceeded: spent > limit; warning: >= 80% used; ok otherwise."""
    if spent > limit:
        return "exceeded"
    used = pct(spent, limit)
    return "warning" if used is not None and used >= WARNING_PCT else "ok"


class BudgetService:
    def __init__(self, db: Session, user: User, today: date | None = None) -> None:
        self.db, self.user = db, user
        self.today = today or date.today()
        self.repo = BudgetRepo(db, user.id)
        self.cats = CategoryRepo(db, user.id)
        self.txs = TransactionRepo(db, user.id)

    def get(self, budget_id: int) -> Budget:
        b = self.repo.get(budget_id)
        if not b:
            raise NotFoundError("Budget not found", code="BUDGET_NOT_FOUND")
        return b

    def _items(self, items: list[BudgetItemIn]) -> list[BudgetItem]:
        seen: set[int] = set()
        out = []
        for it in items:
            cat = self.cats.get(it.category_id)
            if not cat:
                raise NotFoundError(f"Category {it.category_id} not found", code="CATEGORY_NOT_FOUND")
            if cat.kind != "expense":
                raise ValidationFailedError("Budgets apply to expense categories only", code="INVALID_CATEGORY")
            if cat.id in seen:
                raise ValidationFailedError("Duplicate category in budget", code="DUPLICATE_CATEGORY")
            seen.add(cat.id)
            out.append(BudgetItem(category_id=cat.id, limit_amount=it.limit_amount, user_id=self.user.id))
        return out

    def create(self, data: BudgetIn) -> Budget:
        if self.repo.get_by_name(data.name):
            raise ConflictError("A budget with this name already exists", code="BUDGET_EXISTS")
        budget = self.repo.add(Budget(name=data.name.strip(), items=self._items(data.items)))
        audit(self.db, self.user.id, "budget.create", "budget", budget.id)
        self.db.commit()
        return budget

    def update(self, budget_id: int, data: BudgetUpdate) -> Budget:
        budget = self.get(budget_id)
        if data.name and data.name.lower() != budget.name.lower():
            if self.repo.get_by_name(data.name):
                raise ConflictError("A budget with this name already exists", code="BUDGET_EXISTS")
            budget.name = data.name.strip()
        if data.status:
            budget.status = data.status
        if data.items is not None:
            budget.items.clear()
            self.db.flush()
            budget.items.extend(self._items(data.items))
        audit(self.db, self.user.id, "budget.update", "budget", budget.id)
        self.db.commit()
        return budget

    def delete(self, budget_id: int, hard: bool = False) -> None:
        budget = self.get(budget_id)
        if hard:
            self.repo.delete(budget)
        else:
            budget.status = "archived"
        audit(self.db, self.user.id, "budget.delete" if hard else "budget.archive", "budget", budget_id)
        self.db.commit()

    # ---- status (all percentages computed here, never by the LLM) -------------------------------
    def status(self, budget: Budget, month: str | None = None) -> dict:
        first, last, month_label = resolve_month(month, self.today)
        spent_by_cat = {cid: total for cid, _, total, _ in
                        self.txs.by_category(first, last, self.user.currency)}
        items, total_limit, total_spent = [], ZERO, ZERO
        for it in sorted(budget.items, key=lambda i: i.category.name):
            spent = q2(spent_by_cat.get(it.category_id, Decimal(0)))
            items.append({"category_id": it.category_id, "category": it.category.name,
                          "limit": q2(it.limit_amount), "spent": spent,
                          "remaining": q2(it.limit_amount - spent), "used_pct": pct(spent, it.limit_amount),
                          "state": usage_state(spent, it.limit_amount)})
            total_limit += it.limit_amount
            total_spent += spent
        return {"budget_id": budget.id, "name": budget.name, "month": month_label, "items": items,
                "total_limit": q2(total_limit), "total_spent": q2(total_spent),
                "total_remaining": q2(total_limit - total_spent), "used_pct": pct(total_spent, total_limit),
                "state": usage_state(total_spent, total_limit)}

    def all_status(self, month: str | None = None) -> list[dict]:
        return [self.status(b, month) for b in self.repo.list("active")]
