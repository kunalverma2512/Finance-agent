from datetime import date, timedelta
from decimal import Decimal

from app.services.anomaly import evaluate_amount
from tests.conftest import add_tx
from tests.test_budgets_goals import make_budget


def D(x):
    return Decimal(str(x))


def test_evaluate_amount_spec_example():
    typical = [D(x) for x in (20, 25, 30, 35, 40, 28, 33)]
    r = evaluate_amount(D(480), typical)
    assert r is not None and r.typical == D("30.00") and r.score > D("0.9")


def test_normal_variation_not_flagged():
    assert evaluate_amount(D(38), [D(x) for x in (20, 25, 30, 35, 40, 28, 33)]) is None


def test_insufficient_history_not_flagged():
    assert evaluate_amount(D(9999), [D(10), D(11)]) is None


def test_constant_history_flags_only_big_jumps():
    steady = [D("15.99")] * 6
    assert evaluate_amount(D("16.99"), steady) is None
    assert evaluate_amount(D("99.00"), steady) is not None


def test_earlier_outlier_does_not_mask_new_one():
    history = [D(x) for x in (20, 22, 25, 27, 30, 28, 600)]
    assert evaluate_amount(D(500), history) is not None  # median/MAD is robust, mean/std would not be


def test_anomaly_endpoint_and_wording(client, auth, account):
    for i in range(8):
        add_tx(client, auth, account["id"], 20 + i, description="Corner Cafe", on=date.today() - timedelta(days=10 + i))
    add_tx(client, auth, account["id"], 480, description="Corner Cafe")
    found = client.get("/api/v1/analytics/anomalies", headers=auth).json()
    assert len(found) == 1 and found[0]["amount"] == "480.00"
    assert "unusual" in found[0]["reason"] and "fraud determination" in found[0]["reason"]


def test_monitoring_is_idempotent(client, auth, account, db):
    for i in range(8):
        add_tx(client, auth, account["id"], 20 + i, description="Corner Cafe", on=date.today() - timedelta(days=3 + i % 3))
    add_tx(client, auth, account["id"], 480, description="Corner Cafe")
    make_budget(client, auth, "100", "Food")
    first = client.post("/api/v1/monitoring/run", headers=auth).json()
    assert first["unusual"] == 1 and first["budget"] == 1
    second = client.post("/api/v1/monitoring/run", headers=auth).json()
    assert second == {"unusual": 0, "budget": 0, "goal": 0, "insight": 0}
    alerts = client.get("/api/v1/alerts", headers=auth).json()
    assert alerts["total"] == 2 and {a["type"] for a in alerts["items"]} == {"UNUSUAL_TRANSACTION", "BUDGET_EXCEEDED"}


def test_budget_warning_then_exceeded_are_distinct_alerts(client, auth, account):
    make_budget(client, auth, "100", "Food")
    add_tx(client, auth, account["id"], 85, description="Pizza")
    client.post("/api/v1/monitoring/run", headers=auth)
    assert client.get("/api/v1/alerts", headers=auth).json()["items"][0]["type"] == "BUDGET_WARNING"
    add_tx(client, auth, account["id"], 30, description="Pizza")
    client.post("/api/v1/monitoring/run", headers=auth)
    types = [a["type"] for a in client.get("/api/v1/alerts", headers=auth).json()["items"]]
    assert sorted(types) == ["BUDGET_EXCEEDED", "BUDGET_WARNING"]


def test_monthly_insight_alert_created_once(client, auth, account):
    prev = date.today().replace(day=1) - timedelta(days=1)
    add_tx(client, auth, account["id"], 3000, "income", "Payroll", on=prev.replace(day=1))
    add_tx(client, auth, account["id"], 1000, "expense", "Rent", on=prev.replace(day=3))
    client.post("/api/v1/monitoring/run", headers=auth)
    client.post("/api/v1/monitoring/run", headers=auth)
    alerts = client.get("/api/v1/alerts", headers=auth).json()["items"]
    insight = [a for a in alerts if a["type"] == "MONTHLY_INSIGHT"]
    assert len(insight) == 1 and "66.67%" in insight[0]["message"]
    assert client.get("/api/v1/insights", headers=auth).json()[0]["data"]["net"] == "2000.00"


def test_alert_state_transitions(client, auth, account):
    make_budget(client, auth, "10", "Food")
    add_tx(client, auth, account["id"], 50, description="Pizza")
    client.post("/api/v1/monitoring/run", headers=auth)
    a = client.get("/api/v1/alerts?status=unread", headers=auth).json()["items"][0]
    r = client.patch(f"/api/v1/alerts/{a['id']}", json={"status": "read"}, headers=auth).json()
    assert r["status"] == "read"
    assert client.get("/api/v1/alerts?status=unread", headers=auth).json()["total"] == 0
    assert client.patch(f"/api/v1/alerts/{a['id']}", json={"status": "bogus"}, headers=auth).status_code == 422
    client.patch(f"/api/v1/alerts/{a['id']}", json={"status": "unread"}, headers=auth)
    assert client.post("/api/v1/alerts/mark-all-read", headers=auth).status_code == 200
    assert client.patch(f"/api/v1/alerts/{a['id']}", json={"status": "dismissed"}, headers=auth).json()["status"] == "dismissed"


def test_run_all_users_sweep_and_lock(db, client, auth, account):
    from app.db.session import get_sessionmaker
    from app.services.monitoring import ADVISORY_LOCK_ID, run_all_users
    from sqlalchemy import text
    add_tx(client, auth, account["id"], 50, description="Pizza")
    make_budget(client, auth, "10", "Food")
    totals = run_all_users(get_sessionmaker())
    assert totals["users"] == 1 and totals["budget"] == 1
    with get_sessionmaker()() as other:  # another instance holding the lock => sweep is skipped
        other.execute(text("SELECT pg_advisory_lock(:i)"), {"i": ADVISORY_LOCK_ID})
        assert run_all_users(get_sessionmaker())["users"] == 0
        other.execute(text("SELECT pg_advisory_unlock(:i)"), {"i": ADVISORY_LOCK_ID})
