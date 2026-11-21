from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.api.deps import DB, LLM, CurrentUser
from app.core.config import get_settings
from app.core.errors import PayloadTooLargeError
from app.repositories.finance import CategoryRepo, RuleRepo, TxFilter
from app.schemas.common import Message, Page
from app.schemas.finance import (AccountIn, AccountOut, AccountUpdate, AlertOut, AlertUpdate, CategoryIn,
                                 CategoryOut, ImportSummary, RuleIn, RuleOut, TransactionIn, TransactionOut,
                                 TransactionUpdate)
from app.services.accounts import AccountService
from app.services.alerts import AlertService
from app.services.categorization import CategorizationService
from app.services.csv_import import TransactionImportService
from app.services.transactions import TransactionService

router = APIRouter()


# ---- accounts ---------------------------------------------------------------------------------
@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(user: CurrentUser, db: DB, include_archived: bool = False):
    return AccountService(db, user).list_with_balance(include_archived)


@router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(data: AccountIn, user: CurrentUser, db: DB):
    svc = AccountService(db, user)
    return svc.out(svc.create(data))


@router.patch("/accounts/{account_id}", response_model=AccountOut)
def update_account(account_id: int, data: AccountUpdate, user: CurrentUser, db: DB):
    svc = AccountService(db, user)
    return svc.out(svc.update(account_id, data))


# ---- categories & rules -----------------------------------------------------------------------
@router.get("/categories", response_model=list[CategoryOut])
def list_categories(user: CurrentUser, db: DB, kind: Literal["income", "expense"] | None = None):
    return CategoryRepo(db, user.id).list(kind)


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryIn, user: CurrentUser, db: DB):
    return CategorizationService(db, user).create_category(data.name, data.kind)


@router.get("/category-rules", response_model=list[RuleOut])
def list_rules(user: CurrentUser, db: DB):
    return RuleRepo(db, user.id).list()


@router.post("/category-rules", response_model=RuleOut, status_code=201)
def create_rule(data: RuleIn, user: CurrentUser, db: DB):
    return CategorizationService(db, user).create_rule(data.pattern, data.category_id)


@router.delete("/category-rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, user: CurrentUser, db: DB):
    CategorizationService(db, user).delete_rule(rule_id)


# ---- transactions -----------------------------------------------------------------------------
@router.get("/transactions", response_model=Page[TransactionOut])
def list_transactions(
    user: CurrentUser, db: DB,
    date_from: date | None = None, date_to: date | None = None, account_id: int | None = None,
    category_id: int | None = None, direction: Literal["income", "expense"] | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    min_amount: Decimal | None = None, max_amount: Decimal | None = None, uncategorized: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50, offset: Annotated[int, Query(ge=0)] = 0,
):
    f = TxFilter(date_from, date_to, account_id, category_id, direction, search, min_amount, max_amount,
                 uncategorized)
    rows, total = TransactionService(db, user).list(f, limit, offset)
    return Page(items=[TransactionOut.from_tx(t) for t in rows], total=total, limit=limit, offset=offset)


@router.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(data: TransactionIn, user: CurrentUser, db: DB, llm: LLM):
    return TransactionOut.from_tx(TransactionService(db, user, llm).create(data))


@router.post("/transactions/import", response_model=ImportSummary)
async def import_transactions(
    user: CurrentUser, db: DB, llm: LLM, file: Annotated[UploadFile, File()],
    account_id: Annotated[int, Form()],
    amount_convention: Annotated[Literal["signed", "inverted"], Form()] = "signed",
    date_format: Annotated[str | None, Form(max_length=20)] = None,
    use_llm: Annotated[bool, Form()] = False,
):
    limit = get_settings().max_upload_bytes
    data = bytearray()
    while chunk := await file.read(64 * 1024):  # never buffer more than the limit
        data.extend(chunk)
        if len(data) > limit:
            raise PayloadTooLargeError(f"File exceeds {get_settings().max_upload_mb} MB limit")
    return TransactionImportService(db, user, llm).import_csv(
        account_id, bytes(data), file.filename or "", amount_convention=amount_convention,
        date_format=date_format, use_llm=use_llm)


@router.post("/transactions/recategorize", response_model=dict)
def recategorize(user: CurrentUser, db: DB, llm: LLM, use_llm: bool = False):
    return CategorizationService(db, user, llm).recategorize_uncategorized(use_llm)


@router.get("/transactions/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: int, user: CurrentUser, db: DB):
    return TransactionOut.from_tx(TransactionService(db, user).get(tx_id))


@router.patch("/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, data: TransactionUpdate, user: CurrentUser, db: DB):
    return TransactionOut.from_tx(TransactionService(db, user).update(tx_id, data))


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, user: CurrentUser, db: DB):
    TransactionService(db, user).delete(tx_id)


# ---- alerts -----------------------------------------------------------------------------------
@router.get("/alerts", response_model=Page[AlertOut])
def list_alerts(user: CurrentUser, db: DB, status: Literal["unread", "read", "dismissed"] | None = None,
                limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0):
    rows, total = AlertService(db, user).page(status, limit, offset)
    return Page(items=[AlertOut.model_validate(a) for a in rows], total=total, limit=limit, offset=offset)


@router.patch("/alerts/{alert_id}", response_model=AlertOut)
def update_alert(alert_id: int, data: AlertUpdate, user: CurrentUser, db: DB):
    return AlertService(db, user).set_status(alert_id, data.status)


@router.post("/alerts/mark-all-read", response_model=Message)
def mark_all_read(user: CurrentUser, db: DB):
    n = AlertService(db, user).mark_all_read()
    return Message(message=f"{n} alert(s) marked as read")
