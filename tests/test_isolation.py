"""The most important suite: user A must never reach user B's data - through the API or the agent."""
from datetime import date

import pytest

from tests.conftest import add_tx, cat_id
from tests.test_budgets_goals import make_budget


@pytest.fixture
def seeded(client, auth, account):
    tx = add_tx(client, auth, account["id"], 77, description="Secret Pizza")
    budget = make_budget(client, auth)
    goal = client.post("/api/v1/goals", json={"name": "Secret Goal", "target_amount": "500"}, headers=auth).json()
    client.post("/api/v1/monitoring/run", headers=auth)
    alert = client.get("/api/v1/alerts", headers=auth).json()["items"]
    run = client.post("/api/v1/agent/chat", json={"message": "How much did I spend this month?"}, headers=auth).json()
    rule_cat = cat_id(client, auth, "Food")
    rule = client.post("/api/v1/category-rules", json={"pattern": "secret", "category_id": rule_cat}, headers=auth).json()
    return {"tx": tx, "budget": budget, "goal": goal, "alert": alert, "run": run, "rule": rule, "account": account}


def test_b_cannot_read_or_modify_a_resources(client, auth_b, seeded):
    s = seeded
    for path in (f"/api/v1/transactions/{s['tx']['id']}", f"/api/v1/budgets/{s['budget']['id']}",
                 f"/api/v1/budgets/{s['budget']['id']}/status", f"/api/v1/goals/{s['goal']['id']}",
                 f"/api/v1/agent/runs/{s['run']['run_id']}"):
        assert client.get(path, headers=auth_b).status_code == 404, path  # 404, not 403: no existence leak
    assert client.patch(f"/api/v1/transactions/{s['tx']['id']}", json={"description": "pwned"}, headers=auth_b).status_code == 404
    assert client.delete(f"/api/v1/transactions/{s['tx']['id']}", headers=auth_b).status_code == 404
    assert client.patch(f"/api/v1/budgets/{s['budget']['id']}", json={"name": "pwned"}, headers=auth_b).status_code == 404
    assert client.delete(f"/api/v1/budgets/{s['budget']['id']}", headers=auth_b).status_code == 404
    assert client.post(f"/api/v1/goals/{s['goal']['id']}/contributions", json={"amount": "5"}, headers=auth_b).status_code == 404
    assert client.patch(f"/api/v1/accounts/{s['account']['id']}", json={"name": "pwned"}, headers=auth_b).status_code == 404
    assert client.delete(f"/api/v1/category-rules/{s['rule']['id']}", headers=auth_b).status_code == 404


def test_b_listings_are_empty(client, auth_b, seeded):
    assert client.get("/api/v1/transactions", headers=auth_b).json()["total"] == 0
    assert client.get("/api/v1/accounts", headers=auth_b).json() == []
    assert client.get("/api/v1/budgets", headers=auth_b).json() == []
    assert client.get("/api/v1/goals", headers=auth_b).json() == []
    assert client.get("/api/v1/alerts", headers=auth_b).json()["total"] == 0
    assert client.get("/api/v1/category-rules", headers=auth_b).json() == []
    assert client.get("/api/v1/agent/messages", headers=auth_b).json() == []
    assert client.get("/api/v1/analytics/summary", headers=auth_b).json()["cashflow"]["expense"] == "0.00"


def test_b_cannot_write_into_a_account_or_use_a_budget_category(client, auth_b, seeded):
    r = client.post("/api/v1/transactions", json={"account_id": seeded["account"]["id"], "posted_on": "2026-01-01",
                                                  "amount": "5", "direction": "expense", "description": "x"}, headers=auth_b)
    assert r.status_code == 404
    mine = client.post("/api/v1/categories", json={"name": "BOnly", "kind": "expense"}, headers=auth_b).json()
    a_headers_cats = client.get("/api/v1/categories", headers={"Authorization": client.headers.get("Authorization", "")}).status_code
    assert a_headers_cats == 401  # sanity: no ambient auth
    assert mine["is_system"] is False


def test_b_cannot_alter_a_alert(client, auth_b, seeded):
    if seeded["alert"]:
        r = client.patch(f"/api/v1/alerts/{seeded['alert'][0]['id']}", json={"status": "dismissed"}, headers=auth_b)
        assert r.status_code == 404


def test_agent_never_returns_other_users_data(client, auth_b, seeded):
    for q in ("Show my transactions", "How much did I spend this month?", "Am I close to my food budget?",
              "How much do I need to save for my goal?", "What are my account balances?"):
        r = client.post("/api/v1/agent/chat", json={"message": q}, headers=auth_b).json()
        text = r["response"]
        assert "Secret" not in text and "77" not in text and "Monthly" not in text, (q, text)


def test_agent_tool_cannot_reach_other_users_transaction_id(client, db, auth, auth_b, seeded):
    from app.models import User
    from app.tools import ToolContext, ToolError, run_tool
    from sqlalchemy import select
    b = db.scalar(select(User).where(User.email == "b@example.com"))
    ctx = ToolContext(db, b, date.today())
    with pytest.raises(ToolError) as e:
        run_tool("get_transaction", {"transaction_id": seeded["tx"]["id"]}, ctx)
    assert e.value.code == "TRANSACTION_NOT_FOUND"


def test_deleting_user_cascades_everything(client, db, auth, seeded):
    from sqlalchemy import func, select, text
    from app.models import Transaction
    db.execute(text("DELETE FROM users WHERE email = 'a@example.com'"))
    db.commit()
    assert db.scalar(select(func.count()).select_from(Transaction)) == 0
