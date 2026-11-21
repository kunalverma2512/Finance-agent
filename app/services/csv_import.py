"""CSV ingestion pipeline: validate -> parse -> normalise -> dedupe -> persist -> categorise -> analyse."""
import csv
import io
import re
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError, PayloadTooLargeError, ValidationFailedError
from app.integrations.llm import LLMClient
from app.models import User
from app.repositories.finance import AccountRepo, TransactionRepo
from app.schemas.finance import ImportSummary
from app.services.anomaly import AnomalyService
from app.services.audit import audit
from app.services.categorization import CategorizationService
from app.services.transactions import make_fingerprint
from app.utils.text import clean_text, normalize_merchant

ALIASES = {
    "date": {"date", "posted", "posted_on", "posted date", "transaction date", "trans date", "booking date",
             "post date"},
    "description": {"description", "memo", "details", "name", "payee", "narrative", "merchant",
                    "transaction description"},
    "amount": {"amount", "amt", "value", "transaction amount"},
    "debit": {"debit", "withdrawal", "withdrawals", "money out", "paid out"},
    "credit": {"credit", "deposit", "deposits", "money in", "paid in"},
    "type": {"type", "transaction type", "direction", "dr/cr"},
    "currency": {"currency", "ccy"},
}
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%b-%Y", "%d %b %Y", "%b %d, %Y"]
EXPENSE_WORDS = {"debit", "expense", "withdrawal", "dr", "purchase", "payment", "out"}
INCOME_WORDS = {"credit", "income", "deposit", "cr", "refund", "in"}
MAX_ABS = Decimal("1000000000000")
MAX_ERRORS_REPORTED = 20


class RowError(Exception):
    pass


def parse_date(raw: str, fmt: str | None, today: date) -> date:
    raw = raw.strip()
    if not raw:
        raise RowError("missing date")
    formats = [fmt] if fmt else DATE_FORMATS
    for f in formats:
        try:
            d = datetime.strptime(raw, f).date()
            break
        except ValueError:
            continue
    else:
        raise RowError(f"invalid date '{raw[:30]}'")
    if d.year < 1990 or d > today + timedelta(days=2):
        raise RowError(f"date out of range '{raw[:30]}'")
    return d


def parse_amount(raw: str) -> Decimal:
    s = raw.strip()
    if not s:
        raise RowError("missing amount")
    negative = (s.startswith("(") and s.endswith(")")) or s.startswith("-") or s.endswith("-")
    s = re.sub(r"[^\d.,]", "", s)
    if not s or not re.search(r"\d", s):
        raise RowError(f"invalid amount '{raw[:30]}'")
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) and s.count(",") == 1 else s.replace(",", "")
    try:
        value = Decimal(s)
    except InvalidOperation as exc:
        raise RowError(f"invalid amount '{raw[:30]}'") from exc
    if not value.is_finite() or value > MAX_ABS:
        raise RowError("amount out of range")
    value = value.quantize(Decimal("0.01"))
    return -value if negative else value


def decode_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


class TransactionImportService:
    def __init__(self, db: Session, user: User, llm: LLMClient | None = None) -> None:
        self.db, self.user, self.llm = db, user, llm
        self.settings = get_settings()
        self.accounts = AccountRepo(db, user.id)
        self.txs = TransactionRepo(db, user.id)

    def import_csv(self, account_id: int, data: bytes, filename: str, *, amount_convention: str = "signed",
                   date_format: str | None = None, use_llm: bool = False,
                   today: date | None = None) -> ImportSummary:
        today = today or date.today()
        account = self.accounts.get(account_id)
        if not account:
            raise NotFoundError("Account not found", code="ACCOUNT_NOT_FOUND")
        if amount_convention not in ("signed", "inverted"):
            raise ValidationFailedError("amount_convention must be 'signed' or 'inverted'",
                                        code="INVALID_CONVENTION")
        text = self._validate_and_decode(data, filename)
        rows, mapping, ignored = self._read(text)

        batch_id = str(uuid.uuid4())
        errors: list[dict] = []
        parsed: list[dict] = []
        occurrences: Counter[str] = Counter()
        for line_no, raw in rows:
            try:
                rec = self._parse_row(raw, mapping, account.currency, amount_convention, date_format, today)
            except RowError as exc:
                if len(errors) < MAX_ERRORS_REPORTED:
                    errors.append({"row": line_no, "error": str(exc)})
                parsed.append({"_error": True})
                continue
            key = f"{rec['posted_on']}|{rec['amount']}|{rec['direction']}|{normalize_merchant(rec['description'])}"
            occurrences[key] += 1  # identical rows inside ONE file are legitimate (two coffees)
            rec["fingerprint"] = make_fingerprint(account.id, rec["posted_on"], rec["amount"], rec["direction"],
                                                  rec["description"], occurrences[key])
            parsed.append(rec)

        good = [r for r in parsed if "_error" not in r]
        rejected = len(parsed) - len(good)
        existing = self.txs.existing_fingerprints([r["fingerprint"] for r in good])
        fresh = [r for r in good if r["fingerprint"] not in existing]
        for r in fresh:
            r.update(account_id=account.id, currency=account.currency, import_batch_id=batch_id)
        new_ids = self.txs.bulk_insert(fresh)
        duplicates = len(good) - len(new_ids)

        stats = CategorizationService(self.db, self.user, self.llm).categorize_ids(new_ids, use_llm)
        flagged = AnomalyService(self.db, self.user, today=today).detect_for_ids(new_ids)
        audit(self.db, self.user.id, "transactions.import", "account", account.id, batch_id=batch_id,
              imported=len(new_ids), duplicates=duplicates, rejected=rejected)
        self.db.commit()
        categorized = len(new_ids) - stats["unresolved"]
        return ImportSummary(batch_id=batch_id, total_rows=len(parsed), imported=len(new_ids),
                             duplicates=duplicates, rejected=rejected, categorized=categorized,
                             uncategorized=stats["unresolved"], anomalies_flagged=len(flagged),
                             ignored_columns=ignored, errors=errors)

    # ---- stages ---------------------------------------------------------------------------------
    def _validate_and_decode(self, data: bytes, filename: str) -> str:
        if not filename.lower().endswith(".csv"):
            raise ValidationFailedError("Only .csv files are accepted", code="INVALID_FILE_TYPE")
        if len(data) > self.settings.max_upload_bytes:
            raise PayloadTooLargeError(f"File exceeds {self.settings.max_upload_mb} MB limit")
        if not data.strip():
            raise ValidationFailedError("The file is empty", code="EMPTY_FILE")
        if b"\x00" in data[:4096]:
            raise ValidationFailedError("File does not look like a text CSV", code="INVALID_FILE_TYPE")
        return decode_bytes(data)

    def _read(self, text: str):
        sample = text[:4096]
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
        try:
            header = next(reader)
            norm = [h.strip().lower() for h in header]
            mapping: dict[str, int] = {}
            for field, names in ALIASES.items():
                for idx, h in enumerate(norm):
                    if h in names and field not in mapping:
                        mapping[field] = idx
            missing = [f for f in ("date", "description") if f not in mapping]
            if "amount" not in mapping and not ("debit" in mapping or "credit" in mapping):
                missing.append("amount (or debit/credit)")
            if missing:
                raise ValidationFailedError(f"Missing required column(s): {', '.join(missing)}",
                                            code="MISSING_COLUMNS", details={"found": norm})
            used = set(mapping.values())
            ignored = [header[i].strip() for i in range(len(header)) if i not in used]
            rows: list[tuple[int, list[str]]] = []
            for line_no, row in enumerate(reader, start=2):
                if not any(c.strip() for c in row):
                    continue
                if len(rows) >= self.settings.max_import_rows:
                    raise ValidationFailedError(f"Too many rows (limit {self.settings.max_import_rows})",
                                                code="TOO_MANY_ROWS")
                rows.append((line_no, row))
        except csv.Error as exc:
            raise ValidationFailedError("Malformed CSV file", code="MALFORMED_CSV") from exc
        except StopIteration as exc:
            raise ValidationFailedError("The file is empty", code="EMPTY_FILE") from exc
        if not rows:
            raise ValidationFailedError("The file has a header but no data rows", code="EMPTY_FILE")
        return rows, {**mapping, "_width": len(header)}, ignored

    def _parse_row(self, row: list[str], mapping: dict, account_currency: str, convention: str,
                   date_format: str | None, today: date) -> dict:
        if len(row) != mapping["_width"]:
            raise RowError("unexpected number of fields")

        def cell(name: str) -> str:
            return row[mapping[name]] if name in mapping else ""

        posted_on = parse_date(cell("date"), date_format, today)
        description = clean_text(cell("description")) or "(no description)"
        if cell("currency").strip() and cell("currency").strip().upper() != account_currency:
            raise RowError(f"currency {cell('currency').strip().upper()[:5]} does not match account "
                           f"currency {account_currency}")
        if "debit" in mapping or "credit" in mapping:
            debit = parse_amount(cell("debit")) if cell("debit").strip() else Decimal(0)
            credit = parse_amount(cell("credit")) if cell("credit").strip() else Decimal(0)
            if debit and credit:
                raise RowError("both debit and credit are set")
            if not debit and not credit:
                raise RowError("zero or missing amount")
            direction, amount = ("expense", abs(debit)) if debit else ("income", abs(credit))
        else:
            value = parse_amount(cell("amount"))
            if value == 0:
                raise RowError("zero amount")
            if "type" in mapping and cell("type").strip():
                word = cell("type").strip().lower()
                if word in EXPENSE_WORDS:
                    direction = "expense"
                elif word in INCOME_WORDS:
                    direction = "income"
                else:
                    raise RowError(f"unknown transaction type '{word[:20]}'")
            else:
                negative_means_expense = convention == "signed"
                direction = "expense" if (value < 0) == negative_means_expense else "income"
            amount = abs(value)
        return {"posted_on": posted_on, "amount": amount, "direction": direction, "description": description,
                "merchant": normalize_merchant(description)}
