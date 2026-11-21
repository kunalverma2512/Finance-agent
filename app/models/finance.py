from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric,
                        String, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

MONEY = Numeric(18, 2)


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "name"),
        CheckConstraint("type IN ('checking','savings','credit_card','cash','other')", name="type_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(20), default="checking")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    opening_balance: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0.00"),
                                                     server_default="0")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Reserved for future financial-API integrations (see integrations/financial_provider.py).
    provider: Mapped[str | None] = mapped_column(String(40))
    external_id: Mapped[str | None] = mapped_column(String(120))


class Category(Base):
    """user_id NULL = system category visible to everybody."""
    __tablename__ = "categories"
    __table_args__ = (
        Index("uq_categories_system_name", "name", unique=True, postgresql_where=text("user_id IS NULL")),
        Index("uq_categories_user_name", "user_id", "name", unique=True,
              postgresql_where=text("user_id IS NOT NULL")),
        CheckConstraint("kind IN ('income','expense')", name="kind_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(10))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class CategoryRule(TimestampMixin, Base):
    """User-defined 'merchant contains X -> category Y' rule."""
    __tablename__ = "category_rules"
    __table_args__ = (UniqueConstraint("user_id", "pattern"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    pattern: Mapped[str] = mapped_column(String(120))  # stored lower-case
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    priority: Mapped[int] = mapped_column(Integer, default=100, server_default="100")


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "fingerprint"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("direction IN ('income','expense')", name="direction_valid"),
        CheckConstraint("category_source IS NULL OR category_source IN ('RULE','ML','LLM','USER')",
                        name="category_source_valid"),
        Index("ix_transactions_user_posted", "user_id", "posted_on"),
        Index("ix_transactions_user_category_posted", "user_id", "category_id", "posted_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    posted_on: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(MONEY)  # always positive; sign lives in `direction`
    direction: Mapped[str] = mapped_column(String(10))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    description: Mapped[str] = mapped_column(String(500))
    merchant: Mapped[str] = mapped_column(String(255), default="")
    category_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    category_source: Mapped[str | None] = mapped_column(String(4))
    categorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    anomaly_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))
    fingerprint: Mapped[str] = mapped_column(String(64))
    import_batch_id: Mapped[str | None] = mapped_column(String(36))

    category: Mapped[Category | None] = relationship(lazy="joined")
