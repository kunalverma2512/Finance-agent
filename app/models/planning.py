from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.finance import MONEY, Category
from app.models.mixins import TimestampMixin


class Budget(TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "name"),
        CheckConstraint("status IN ('active','archived')", name="status_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    period: Mapped[str] = mapped_column(String(10), default="monthly")
    status: Mapped[str] = mapped_column(String(10), default="active", server_default="active")
    items: Mapped[list["BudgetItem"]] = relationship(cascade="all, delete-orphan", lazy="selectin",
                                                     back_populates="budget")


class BudgetItem(TimestampMixin, Base):
    __tablename__ = "budget_items"
    __table_args__ = (
        UniqueConstraint("budget_id", "category_id"),
        CheckConstraint("limit_amount > 0", name="limit_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    limit_amount: Mapped[Decimal] = mapped_column(MONEY)
    budget: Mapped[Budget] = relationship(back_populates="items")
    category: Mapped[Category] = relationship(lazy="joined")


class FinancialGoal(TimestampMixin, Base):
    __tablename__ = "financial_goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="target_positive"),
        CheckConstraint("current_amount >= 0", name="current_non_negative"),
        CheckConstraint("status IN ('active','completed','archived')", name="status_valid"),
        UniqueConstraint("user_id", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[Decimal] = mapped_column(MONEY)
    current_amount: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0.00"), server_default="0")
    deadline: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="active", server_default="active")
