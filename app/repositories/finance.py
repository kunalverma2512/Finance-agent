from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models import Account, Category, CategoryRule, Transaction
from app.repositories.base import Repo


class AccountRepo(Repo):
    def get(self, account_id: int) -> Account | None:
        return self.db.scalar(select(Account).where(Account.id == account_id,
                                                     Account.user_id == self.user_id))

    def get_by_name(self, name: str) -> Account | None:
        return self.db.scalar(select(Account).where(Account.user_id == self.user_id,
                                                     func.lower(Account.name) == name.lower()))

    def list(self, include_archived: bool = False) -> list[Account]:
        q = select(Account).where(Account.user_id == self.user_id).order_by(Account.name)
        if not include_archived:
            q = q.where(Account.is_archived.is_(False))
        return list(self.db.scalars(q))

    def add(self, account: Account) -> Account:
        account.user_id = self.user_id
        self.db.add(account)
        self.db.flush()
        return account


class CategoryRepo(Repo):
    def _visible(self) -> Select:
        return select(Category).where(or_(Category.user_id.is_(None), Category.user_id == self.user_id))

    def get(self, category_id: int) -> Category | None:
        return self.db.scalar(self._visible().where(Category.id == category_id))

    def get_by_name(self, name: str) -> Category | None:
        return self.db.scalar(self._visible().where(func.lower(Category.name) == name.lower())
                              .order_by(Category.user_id.is_(None)))  # user category wins over system

    def list(self, kind: str | None = None) -> list[Category]:
        q = self._visible().order_by(Category.kind, Category.name)
        if kind:
            q = q.where(Category.kind == kind)
        return list(self.db.scalars(q))

    def add(self, category: Category) -> Category:
        category.user_id = self.user_id
        category.is_system = False
        self.db.add(category)
        self.db.flush()
        return category


class RuleRepo(Repo):
    def list(self) -> list[CategoryRule]:
        return list(self.db.scalars(select(CategoryRule).where(CategoryRule.user_id == self.user_id)
                                    .order_by(CategoryRule.priority.desc(),
                                              func.length(CategoryRule.pattern).desc())))

    def get_by_pattern(self, pattern: str) -> CategoryRule | None:
        return self.db.scalar(select(CategoryRule).where(CategoryRule.user_id == self.user_id,
                                                          CategoryRule.pattern == pattern))

    def get(self, rule_id: int) -> CategoryRule | None:
        return self.db.scalar(select(CategoryRule).where(CategoryRule.id == rule_id,
                                                          CategoryRule.user_id == self.user_id))

    def add(self, rule: CategoryRule) -> CategoryRule:
        rule.user_id = self.user_id
        self.db.add(rule)
        self.db.flush()
        return rule


@dataclass
class TxFilter:
    date_from: date | None = None
    date_to: date | None = None
    account_id: int | None = None
    category_id: int | None = None
    direction: str | None = None
    search: str | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    uncategorized: bool = False
    currency: str | None = None


def _like_escape(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class TransactionRepo(Repo):
    def _scoped(self, f: TxFilter | None = None) -> Select:
        q = select(Transaction).where(Transaction.user_id == self.user_id)
        if f is None:
            return q
        if f.date_from:
            q = q.where(Transaction.posted_on >= f.date_from)
        if f.date_to:
            q = q.where(Transaction.posted_on <= f.date_to)
        if f.account_id:
            q = q.where(Transaction.account_id == f.account_id)
        if f.category_id:
            q = q.where(Transaction.category_id == f.category_id)
        if f.direction:
            q = q.where(Transaction.direction == f.direction)
        if f.currency:
            q = q.where(Transaction.currency == f.currency)
        if f.uncategorized:
            q = q.where(Transaction.category_id.is_(None))
        if f.min_amount is not None:
            q = q.where(Transaction.amount >= f.min_amount)
        if f.max_amount is not None:
            q = q.where(Transaction.amount <= f.max_amount)
        if f.search:
            like = f"%{_like_escape(f.search.strip())}%"
            q = q.where(or_(Transaction.description.ilike(like, escape="\\"),
                            Transaction.merchant.ilike(like, escape="\\")))
        return q

    def get(self, tx_id: int) -> Transaction | None:
        return self.db.scalar(self._scoped().where(Transaction.id == tx_id))

    def get_many(self, ids: list[int]) -> list[Transaction]:
        if not ids:
            return []
        return list(self.db.scalars(self._scoped().where(Transaction.id.in_(ids))))

    def page(self, f: TxFilter, limit: int, offset: int) -> tuple[list[Transaction], int]:
        base = self._scoped(f)
        total = self.db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
        rows = self.db.scalars(base.order_by(Transaction.posted_on.desc(), Transaction.id.desc())
                               .limit(limit).offset(offset))
        return list(rows), total

    def add(self, tx: Transaction) -> Transaction:
        tx.user_id = self.user_id
        self.db.add(tx)
        self.db.flush()
        return tx

    def delete(self, tx: Transaction) -> None:
        self.db.delete(tx)
        self.db.flush()

    def existing_fingerprints(self, fingerprints: list[str]) -> set[str]:
        found: set[str] = set()
        for i in range(0, len(fingerprints), 5000):
            chunk = fingerprints[i:i + 5000]
            found.update(self.db.scalars(select(Transaction.fingerprint).where(
                Transaction.user_id == self.user_id, Transaction.fingerprint.in_(chunk))))
        return found

    def bulk_insert(self, rows: list[dict]) -> list[int]:
        """Insert rows, silently skipping fingerprint conflicts (race-safe dedup). Returns new ids."""
        ids: list[int] = []
        for i in range(0, len(rows), 500):
            chunk = [{**r, "user_id": self.user_id} for r in rows[i:i + 500]]
            stmt = (pg_insert(Transaction).values(chunk)
                    .on_conflict_do_nothing(index_elements=["user_id", "fingerprint"])
                    .returning(Transaction.id))
            ids.extend(self.db.scalars(stmt))
        return ids

    # ---- aggregates (all deterministic SQL, never LLM) -------------------------------------
    def totals(self, start: date, end: date, currency: str) -> dict[str, tuple[Decimal, int]]:
        q = (select(Transaction.direction, func.coalesce(func.sum(Transaction.amount), 0), func.count())
             .where(Transaction.user_id == self.user_id, Transaction.posted_on.between(start, end),
                    Transaction.currency == currency).group_by(Transaction.direction))
        out = {"income": (Decimal("0"), 0), "expense": (Decimal("0"), 0)}
        for direction, total, count in self.db.execute(q):
            out[direction] = (Decimal(total), count)
        return out

    def by_category(self, start: date, end: date, currency: str,
                    direction: str = "expense") -> list[tuple[int | None, str, Decimal, int]]:
        q = (select(Transaction.category_id, func.coalesce(Category.name, "Uncategorized"),
                    func.sum(Transaction.amount), func.count())
             .join(Category, Category.id == Transaction.category_id, isouter=True)
             .where(Transaction.user_id == self.user_id, Transaction.posted_on.between(start, end),
                    Transaction.currency == currency, Transaction.direction == direction)
             .group_by(Transaction.category_id, Category.name).order_by(func.sum(Transaction.amount).desc()))
        return [(cid, name, Decimal(total), count) for cid, name, total, count in self.db.execute(q)]

    def monthly(self, start: date, end: date, currency: str) -> list[tuple[str, str, Decimal]]:
        month = func.to_char(Transaction.posted_on, "YYYY-MM")
        q = (select(month, Transaction.direction, func.sum(Transaction.amount))
             .where(Transaction.user_id == self.user_id, Transaction.posted_on.between(start, end),
                    Transaction.currency == currency)
             .group_by(month, Transaction.direction).order_by(month))
        return [(m, d, Decimal(t)) for m, d, t in self.db.execute(q)]

    def expense_rows_since(self, start: date, currency: str) -> list[tuple[int, date, Decimal, int | None, str]]:
        q = (select(Transaction.id, Transaction.posted_on, Transaction.amount, Transaction.category_id,
                    Transaction.merchant)
             .where(Transaction.user_id == self.user_id, Transaction.direction == "expense",
                    Transaction.posted_on >= start, Transaction.currency == currency))
        return [(i, d, Decimal(a), c, m) for i, d, a, c, m in self.db.execute(q)]

    def merchant_training_rows(self, limit: int = 5000) -> list[tuple[str, int]]:
        """(merchant, category_id) pairs the user (or their rules) labelled - ML training data."""
        q = (select(Transaction.merchant, Transaction.category_id)
             .where(Transaction.user_id == self.user_id, Transaction.category_id.is_not(None),
                    Transaction.category_source.in_(("USER", "RULE")), Transaction.merchant != "")
             .order_by(Transaction.id.desc()).limit(limit))
        return [(m, c) for m, c in self.db.execute(q)]

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Transaction)
                              .where(Transaction.user_id == self.user_id)) or 0
