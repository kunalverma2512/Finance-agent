from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORM, Currency, Money


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: Literal["checking", "savings", "credit_card", "cash", "other"] = "checking"
    currency: Currency = "USD"
    opening_balance: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_archived: bool | None = None


class AccountOut(ORM):
    id: int
    name: str
    type: str
    currency: str
    opening_balance: Decimal
    is_archived: bool
    balance: Decimal | None = None


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: Literal["income", "expense"] = "expense"


class CategoryOut(ORM):
    id: int
    name: str
    kind: str
    is_system: bool


class RuleIn(BaseModel):
    pattern: str = Field(min_length=2, max_length=120)
    category_id: int


class RuleOut(ORM):
    id: int
    pattern: str
    category_id: int


class TransactionIn(BaseModel):
    account_id: int
    posted_on: date
    amount: Money
    direction: Literal["income", "expense"]
    description: str = Field(min_length=1, max_length=500)
    category_id: int | None = None

    @field_validator("description")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("description must not be blank")
        return v


class TransactionUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=500)
    posted_on: date | None = None
    amount: Money | None = None
    category_id: int | None = None
    create_rule: bool = False  # on recategorisation: remember merchant -> category


class TransactionOut(BaseModel):
    id: int
    account_id: int
    category_id: int | None
    category_name: str | None
    posted_on: date
    amount: Decimal
    direction: str
    currency: str
    description: str
    merchant: str
    category_confidence: Decimal | None
    category_source: str | None
    anomaly_score: Decimal | None

    @classmethod
    def from_tx(cls, tx) -> "TransactionOut":
        return cls(id=tx.id, account_id=tx.account_id, category_id=tx.category_id,
                   category_name=tx.category.name if tx.category else None, posted_on=tx.posted_on,
                   amount=tx.amount, direction=tx.direction, currency=tx.currency,
                   description=tx.description, merchant=tx.merchant,
                   category_confidence=tx.category_confidence, category_source=tx.category_source,
                   anomaly_score=tx.anomaly_score)


class ImportSummary(BaseModel):
    batch_id: str
    total_rows: int
    imported: int
    duplicates: int
    rejected: int
    categorized: int
    uncategorized: int
    anomalies_flagged: int
    ignored_columns: list[str]
    errors: list[dict]


class AlertOut(ORM):
    id: int
    type: str
    severity: str
    title: str
    message: str
    status: str
    payload: dict
    created_at: datetime


class AlertUpdate(BaseModel):
    status: Literal["unread", "read", "dismissed"]
