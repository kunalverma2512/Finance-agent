"""Unusual-transaction detection (robust statistics; wording is 'unusual', never 'fraud')."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from sqlalchemy.orm import Session

from app.models import Alert, Transaction, User
from app.repositories.finance import CategoryRepo, TransactionRepo
from app.repositories.planning import AlertRepo
from app.utils.money import q2

MIN_HISTORY = 5
MOD_Z_THRESHOLD = 3.5
MIN_RATIO = Decimal("1.5")
CONSTANT_HISTORY_RATIO = Decimal("3")
LOOKBACK_DAYS = 365
MAX_REFERENCE = 200


@dataclass(frozen=True)
class AnomalyResult:
    score: Decimal  # 0..1
    typical: Decimal
    ratio: Decimal
    sample_size: int


def evaluate_amount(amount: Decimal, reference: list[Decimal]) -> AnomalyResult | None:
    """Modified z-score (median/MAD) so earlier outliers do not mask new ones."""
    if len(reference) < MIN_HISTORY:
        return None
    med = Decimal(median(reference))
    if med <= 0:
        return None
    mad = Decimal(median([abs(x - med) for x in reference]))
    ratio = amount / med
    if mad == 0:  # perfectly regular history (e.g. a fixed subscription)
        if ratio < CONSTANT_HISTORY_RATIO:
            return None
        score = min(Decimal(1), ratio / 10)
    else:
        z = float(Decimal("0.6745") * (amount - med) / mad)
        if z < MOD_Z_THRESHOLD or ratio < MIN_RATIO:
            return None
        score = Decimal(str(min(1.0, z / 10)))
    return AnomalyResult(score=score.quantize(Decimal("0.001")), typical=q2(med), ratio=q2(ratio),
                         sample_size=len(reference))


def describe(result: AnomalyResult, amount: Decimal, scope: str, currency: str) -> str:
    return (f"{currency} {amount:,.2f} is {result.ratio}x the typical {currency} {result.typical:,.2f} "
            f"for {scope} (based on {result.sample_size} similar transactions). "
            "This is flagged as unusual for review - it is not a fraud determination.")


class AnomalyService:
    def __init__(self, db: Session, user: User, today: date | None = None) -> None:
        self.db, self.user = db, user
        self.today = today or date.today()
        self.txs = TransactionRepo(db, user.id)
        self.alerts = AlertRepo(db, user.id)
        self.cat_names = {c.id: c.name for c in CategoryRepo(db, user.id).list()}

    def detect(self, start: date, end: date, persist: bool = True) -> list[dict]:
        return self._run(lambda row: start <= row[1] <= end, persist)

    def detect_for_ids(self, ids: list[int]) -> list[dict]:
        wanted = set(ids)
        return self._run(lambda row: row[0] in wanted, True)

    def _run(self, is_target, persist: bool) -> list[dict]:
        rows = self.txs.expense_rows_since(self.today - timedelta(days=LOOKBACK_DAYS), self.user.currency)
        by_merchant: dict[str, list] = defaultdict(list)
        by_category: dict[int | None, list] = defaultdict(list)
        for row in sorted(rows, key=lambda r: r[1], reverse=True):  # newest first
            if row[4]:
                by_merchant[row[4]].append(row)
            if row[3] is not None:
                by_category[row[3]].append(row)
        findings: list[dict] = []
        for row in rows:
            if not is_target(row):
                continue
            tx_id, posted_on, amount, cat_id, merchant = row
            scope, result = None, None
            others = [r[2] for r in by_merchant.get(merchant, []) if r[0] != tx_id][:MAX_REFERENCE]
            if len(others) >= MIN_HISTORY:
                scope, result = f"'{merchant}'", evaluate_amount(amount, others)
            elif cat_id is not None:
                others = [r[2] for r in by_category[cat_id] if r[0] != tx_id][:MAX_REFERENCE]
                scope = self.cat_names.get(cat_id, "this category")
                result = evaluate_amount(amount, others)
            if result is None:
                continue
            findings.append({"transaction_id": tx_id, "date": posted_on, "amount": q2(amount),
                             "merchant": merchant, "category": self.cat_names.get(cat_id),
                             "score": result.score, "typical_amount": result.typical, "ratio": result.ratio,
                             "reason": describe(result, amount, scope, self.user.currency)})
        findings.sort(key=lambda f: f["score"], reverse=True)
        if persist and findings:
            self._persist(findings)
        return findings

    def _persist(self, findings: list[dict]) -> None:
        tx_map = {t.id: t for t in self.txs.get_many([f["transaction_id"] for f in findings])}
        for f in findings:
            tx: Transaction = tx_map[f["transaction_id"]]
            tx.anomaly_score = f["score"]
            self.alerts.add_if_new(Alert(
                type="UNUSUAL_TRANSACTION", severity="warning", dedupe_key=f"unusual_tx:{tx.id}",
                title=f"Unusual transaction: {f['merchant'] or tx.description[:40]}", message=f["reason"],
                payload={"transaction_id": tx.id, "amount": str(f["amount"]), "score": str(f["score"])}))
