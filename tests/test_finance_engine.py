from datetime import date
from decimal import Decimal

from app.services.finance import detect_recurring, net_cashflow, pct_change, savings_rate
from app.services.goals import months_until, required_monthly
from app.services.budgets import usage_state
from app.utils.periods import resolve_month, shift_month
from tests.conftest import add_tx


def test_cashflow_and_savings_rate_spec_example():
    assert net_cashflow(Decimal("3000"), Decimal("2000")) == Decimal("1000.00")
    assert savings_rate(Decimal("3000"), Decimal("2000")) == Decimal("33.33")


def test_zero_income_has_no_savings_rate():
    assert savings_rate(Decimal("0"), Decimal("50")) is None
    assert pct_change(Decimal("10"), Decimal("0")) is None


def test_negative_savings_rate_when_overspending():
    assert savings_rate(Decimal("1000"), Decimal("1500")) == Decimal("-50.00")


def test_large_values_keep_precision():
    assert net_cashflow(Decimal("999999999999.99"), Decimal("0.01")) == Decimal("999999999999.98")


def test_decimal_never_float_drift():
    total = sum((Decimal("0.10") for _ in range(10)), Decimal(0))
    assert net_cashflow(total, Decimal("1.00")) == Decimal("0.00")


def test_budget_states():
    assert usage_state(Decimal("350"), Decimal("400")) == "warning"  # 87.5%
    assert usage_state(Decimal("100"), Decimal("400")) == "ok"
    assert usage_state(Decimal("400"), Decimal("400")) == "warning"  # at the limit, not over
    assert usage_state(Decimal("400.01"), Decimal("400")) == "exceeded"


def test_goal_math():
    assert months_until(date(2026, 4, 1), date(2026, 1, 1)) == 3
    assert months_until(date(2026, 1, 1), date(2026, 1, 1)) is None
    assert months_until(date(2026, 7, 1), date(2026, 1, 1)) == 6
    assert months_until(date(2026, 7, 2), date(2026, 1, 1)) == 7
    assert months_until(date(2026, 1, 5), date(2026, 1, 1)) == 1
    assert required_monthly(Decimal("1100"), 6) == Decimal("183.34")  # rounded UP so goal is reachable


def test_period_helpers():
    assert resolve_month("last_month", date(2026, 1, 15))[2] == "2025-12"
    assert shift_month(date(2026, 1, 1), -13) == date(2024, 12, 1)


def test_recurring_detection():
    rows = [(date(2026, m, 5), Decimal("15.99"), "netflix") for m in (1, 2, 3)]
    rows += [(date(2026, 1, 9), Decimal("40"), "cafe"), (date(2026, 2, 9), Decimal("90"), "cafe")]
    found = detect_recurring(rows)
    assert [r["merchant"] for r in found] == ["netflix"]


def test_analytics_summary_end_to_end(client, auth, account):
    today = date.today()
    add_tx(client, auth, account["id"], 3000, "income", "Payroll ACME")
    add_tx(client, auth, account["id"], 2000, "expense", "Rent June landlord")
    s = client.get("/api/v1/analytics/summary", headers=auth).json()
    assert s["cashflow"]["net"] == "1000.00"
    assert s["cashflow"]["savings_rate"] == "33.33"
    assert s["category_spending"][0]["category"] == "Rent & Housing"
    assert len(s["monthly_series"]) == 6 and s["month"] == f"{today.year:04d}-{today.month:02d}"


def test_empty_user_analytics_has_no_crashes(client, auth):
    s = client.get("/api/v1/analytics/summary", headers=auth).json()
    assert s["cashflow"]["income"] == "0.00" and s["cashflow"]["savings_rate"] is None


def test_currency_isolation_in_totals(client, auth):
    eur = client.post("/api/v1/accounts", json={"name": "Euro", "currency": "EUR"}, headers=auth).json()
    usd = client.post("/api/v1/accounts", json={"name": "Dollar", "currency": "USD"}, headers=auth).json()
    add_tx(client, auth, eur["id"], 500, "expense", "Hotel Paris")
    add_tx(client, auth, usd["id"], 100, "expense", "Pizza")
    s = client.get("/api/v1/analytics/summary", headers=auth).json()
    assert s["cashflow"]["expense"] == "100.00"  # EUR amounts are never mixed into USD totals


def test_invalid_month_rejected(client, auth):
    assert client.get("/api/v1/analytics/summary?month=2026-13", headers=auth).status_code == 422
