from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORM, Money, MoneyNonNeg


class BudgetItemIn(BaseModel):
    category_id: int
    limit_amount: Money


class BudgetIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    items: list[BudgetItemIn] = Field(min_length=1, max_length=50)


class BudgetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: Literal["active", "archived"] | None = None
    items: list[BudgetItemIn] | None = Field(default=None, min_length=1, max_length=50)  # replaces items


class BudgetItemOut(ORM):
    category_id: int
    limit_amount: Decimal


class BudgetOut(ORM):
    id: int
    name: str
    period: str
    status: str
    items: list[BudgetItemOut]


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_amount: Money
    current_amount: MoneyNonNeg = Decimal("0")
    deadline: date | None = None


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_amount: Money | None = None
    deadline: date | None = None
    status: Literal["active", "archived"] | None = None


class ContributionIn(BaseModel):
    amount: Money


class GoalOut(ORM):
    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: date | None
    status: str
