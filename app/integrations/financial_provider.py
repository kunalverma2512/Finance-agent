"""Extension point for bank/aggregator APIs (Plaid, Open Banking, ...).

No provider is implemented: CSV import is the supported ingestion path today. New providers
implement `FinancialProvider` and feed rows into `TransactionImportService.ingest_rows`.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ExternalTransaction:
    external_id: str
    posted_on: date
    amount: Decimal  # signed: negative = money out
    description: str
    currency: str


class FinancialProvider(Protocol):
    name: str

    def fetch_transactions(self, external_account_id: str, since: date) -> list[ExternalTransaction]: ...
