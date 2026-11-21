import hashlib
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationFailedError
from app.integrations.llm import LLMClient
from app.models import Transaction, User
from app.repositories.finance import AccountRepo, CategoryRepo, TransactionRepo, TxFilter
from app.schemas.finance import TransactionIn, TransactionUpdate
from app.services.audit import audit
from app.services.categorization import CategorizationService
from app.utils.text import clean_text, normalize_merchant


def make_fingerprint(account_id: int, posted_on: date, amount, direction: str, description: str,
                     occurrence: int) -> str:
    base = f"{account_id}|{posted_on.isoformat()}|{amount}|{direction}|{normalize_merchant(description)}|{occurrence}"
    return hashlib.sha256(base.encode()).hexdigest()


class TransactionService:
    def __init__(self, db: Session, user: User, llm: LLMClient | None = None) -> None:
        self.db, self.user = db, user
        self.repo = TransactionRepo(db, user.id)
        self.accounts = AccountRepo(db, user.id)
        self.cats = CategoryRepo(db, user.id)
        self.categorizer = CategorizationService(db, user, llm)

    def get(self, tx_id: int) -> Transaction:
        tx = self.repo.get(tx_id)
        if not tx:
            raise NotFoundError("Transaction not found", code="TRANSACTION_NOT_FOUND")
        return tx

    def list(self, f: TxFilter, limit: int, offset: int):
        return self.repo.page(f, limit, offset)

    def create(self, data: TransactionIn) -> Transaction:
        account = self.accounts.get(data.account_id)
        if not account:
            raise NotFoundError("Account not found", code="ACCOUNT_NOT_FOUND")
        description = clean_text(data.description)
        if not description:
            raise ValidationFailedError("Description must not be blank", code="INVALID_DESCRIPTION")
        tx = Transaction(account_id=account.id, posted_on=data.posted_on, amount=data.amount,
                         direction=data.direction, currency=account.currency, description=description,
                         merchant=normalize_merchant(description),
                         fingerprint="manual:" + uuid.uuid4().hex)  # manual entries are never deduped
        self.repo.add(tx)
        if data.category_id is not None:
            self.categorizer.set_user_category(tx, data.category_id)
        else:
            self.categorizer.categorize_ids([tx.id])
        audit(self.db, self.user.id, "transaction.create", "transaction", tx.id)
        self.db.commit()
        return tx

    def update(self, tx_id: int, data: TransactionUpdate) -> Transaction:
        tx = self.get(tx_id)
        fields = data.model_fields_set
        if "description" in fields and data.description is not None:
            tx.description = clean_text(data.description)
            tx.merchant = normalize_merchant(tx.description)
        if "posted_on" in fields and data.posted_on is not None:
            tx.posted_on = data.posted_on
        if "amount" in fields and data.amount is not None:
            tx.amount = data.amount
        if "category_id" in fields and data.category_id is not None:
            self.categorizer.set_user_category(tx, data.category_id, data.create_rule)
        audit(self.db, self.user.id, "transaction.update", "transaction", tx.id)
        self.db.commit()
        return tx

    def delete(self, tx_id: int) -> None:
        tx = self.get(tx_id)
        self.repo.delete(tx)
        audit(self.db, self.user.id, "transaction.delete", "transaction", tx_id)
        self.db.commit()
