from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Account, Transaction, User
from app.repositories.finance import AccountRepo
from app.schemas.finance import AccountIn, AccountOut, AccountUpdate
from app.services.audit import audit


class AccountService:
    def __init__(self, db: Session, user: User) -> None:
        self.db, self.user = db, user
        self.repo = AccountRepo(db, user.id)

    def get(self, account_id: int) -> Account:
        acc = self.repo.get(account_id)
        if not acc:
            raise NotFoundError("Account not found", code="ACCOUNT_NOT_FOUND")
        return acc

    def create(self, data: AccountIn) -> Account:
        if self.repo.get_by_name(data.name):
            raise ConflictError("An account with this name already exists", code="ACCOUNT_EXISTS")
        acc = self.repo.add(Account(**data.model_dump()))
        audit(self.db, self.user.id, "account.create", "account", acc.id)
        self.db.commit()
        return acc

    def update(self, account_id: int, data: AccountUpdate) -> Account:
        acc = self.get(account_id)
        if data.name is not None and data.name.lower() != acc.name.lower():
            if self.repo.get_by_name(data.name):
                raise ConflictError("An account with this name already exists", code="ACCOUNT_EXISTS")
            acc.name = data.name
        if data.is_archived is not None:
            acc.is_archived = data.is_archived
        self.db.commit()
        return acc

    def _flows(self, account_ids: list[int]) -> dict[int, Decimal]:
        q = (select(Transaction.account_id, Transaction.direction, func.sum(Transaction.amount))
             .where(Transaction.user_id == self.user.id, Transaction.account_id.in_(account_ids))
             .group_by(Transaction.account_id, Transaction.direction))
        net: dict[int, Decimal] = {}
        for acc_id, direction, total in self.db.execute(q):
            net[acc_id] = net.get(acc_id, Decimal("0")) + (Decimal(total) if direction == "income"
                                                           else -Decimal(total))
        return net

    def balances(self, accounts: list[Account]) -> dict[int, Decimal]:
        flows = self._flows([a.id for a in accounts]) if accounts else {}
        return {a.id: a.opening_balance + flows.get(a.id, Decimal("0")) for a in accounts}

    def list_with_balance(self, include_archived: bool = False) -> list[AccountOut]:
        accounts = self.repo.list(include_archived)
        bal = self.balances(accounts)
        return [AccountOut.model_validate(a).model_copy(update={"balance": bal[a.id]}) for a in accounts]

    def out(self, acc: Account) -> AccountOut:
        return AccountOut.model_validate(acc).model_copy(update={"balance": self.balances([acc])[acc.id]})
