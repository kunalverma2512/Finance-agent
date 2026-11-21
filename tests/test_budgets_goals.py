from datetime import date, timedelta

from tests.conftest import add_tx, cat_id


def make_budget(client, auth, limit="400", category="Food", name="Monthly"):
    r = client.post("/api/v1/budgets", json={"name": name, "items": [
        {"category_id": cat_id(client, auth, category), "limit_amount": limit}]}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def test_budget_status_matches_spec_example(client, auth, account):
    b = make_budget(client, auth)
    add_tx(client, auth, account["id"], 350, description="Pizza Palace")
    s = client.get(f"/api/v1/budgets/{b['id']}/status", headers=auth).json()
    item = s["items"][0]
    assert (item["limit"], item["spent"], item["used_pct"], item["remaining"], item["state"]) == \
        ("400.00", "350.00", "87.50", "50.00", "warning")
    assert s["total_spent"] == "350.00" and s["used_pct"] == "87.50"


def test_budget_exceeded_and_only_current_month_counts(client, auth, account):
    b = make_budget(client, auth, "100")
    add_tx(client, auth, account["id"], 150, description="Pizza")
    add_tx(client, auth, account["id"], 999, description="Pizza", on=date.today().replace(day=1) - timedelta(days=1))
    item = client.get(f"/api/v1/budgets/{b['id']}/status", headers=auth).json()["items"][0]
    assert item["spent"] == "150.00" and item["state"] == "exceeded" and item["remaining"] == "-50.00"


def test_budget_validation(client, auth):
    salary = cat_id(client, auth, "Salary")
    r = client.post("/api/v1/budgets", json={"name": "x", "items": [{"category_id": salary, "limit_amount": "5"}]}, headers=auth)
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_CATEGORY"
    food = cat_id(client, auth, "Food")
    r = client.post("/api/v1/budgets", json={"name": "x", "items": [{"category_id": food, "limit_amount": "5"},
                                                                    {"category_id": food, "limit_amount": "6"}]}, headers=auth)
    assert r.json()["error"]["code"] == "DUPLICATE_CATEGORY"
    for bad in ("0", "-5", "abc"):
        assert client.post("/api/v1/budgets", json={"name": "x", "items": [{"category_id": food, "limit_amount": bad}]},
                           headers=auth).status_code == 422
    make_budget(client, auth, name="Same")
    assert client.post("/api/v1/budgets", json={"name": "same", "items": [{"category_id": food, "limit_amount": "5"}]},
                       headers=auth).status_code == 409


def test_budget_update_archive_delete(client, auth):
    b = make_budget(client, auth)
    groceries = cat_id(client, auth, "Groceries")
    r = client.patch(f"/api/v1/budgets/{b['id']}", json={"items": [{"category_id": groceries, "limit_amount": "250"}]}, headers=auth)
    assert [i["category_id"] for i in r.json()["items"]] == [groceries]
    assert client.delete(f"/api/v1/budgets/{b['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/budgets/{b['id']}", headers=auth).json()["status"] == "archived"
    assert client.get("/api/v1/budgets/status", headers=auth).json() == []  # archived budgets are not monitored
    assert client.delete(f"/api/v1/budgets/{b['id']}?hard=true", headers=auth).status_code == 204
    assert client.get(f"/api/v1/budgets/{b['id']}", headers=auth).status_code == 404


def test_goal_progress_and_required_monthly(client, auth):
    from app.utils.periods import add_months
    deadline = (add_months(date.today(), 6) + timedelta(days=1)).isoformat()  # a started 7th month counts
    g = client.post("/api/v1/goals", json={"name": "Laptop", "target_amount": "1500", "current_amount": "400",
                                           "deadline": deadline}, headers=auth).json()
    p = client.get(f"/api/v1/goals/{g['id']}", headers=auth).json()
    assert p["remaining"] == "1100.00" and p["progress_pct"] == "26.67"
    assert p["months_left"] == 7 and p["required_monthly"] == "157.15"
    assert p["pace"] == "unknown"  # no history to judge pace from


def test_goal_contributions_complete_goal(client, auth):
    g = client.post("/api/v1/goals", json={"name": "Trip", "target_amount": "100"}, headers=auth).json()
    r = client.post(f"/api/v1/goals/{g['id']}/contributions", json={"amount": "60"}, headers=auth).json()
    assert r["status"] == "active" and r["current_amount"] == "60.00"
    r = client.post(f"/api/v1/goals/{g['id']}/contributions", json={"amount": "40"}, headers=auth).json()
    assert r["status"] == "completed"
    assert client.get(f"/api/v1/goals/{g['id']}", headers=auth).json()["pace"] == "completed"


def test_goal_validation(client, auth):
    assert client.post("/api/v1/goals", json={"name": "x", "target_amount": "0"}, headers=auth).status_code == 422
    r = client.post("/api/v1/goals", json={"name": "x", "target_amount": "5", "deadline": "2000-01-01"}, headers=auth)
    assert r.json()["error"]["code"] == "INVALID_DEADLINE"
    assert client.post("/api/v1/goals/9999/contributions", json={"amount": "5"}, headers=auth).status_code == 404


def test_goal_pace_uses_history(client, auth, account):
    today = date.today()
    first = today.replace(day=1)
    last_month = first - timedelta(days=1)
    add_tx(client, auth, account["id"], 2000, "income", "Payroll", on=last_month.replace(day=1))
    add_tx(client, auth, account["id"], 1500, "expense", "Rent", on=last_month.replace(day=2))
    deadline = (today + timedelta(days=60)).isoformat()
    g = client.post("/api/v1/goals", json={"name": "Big", "target_amount": "5000", "deadline": deadline}, headers=auth).json()
    p = client.get(f"/api/v1/goals/{g['id']}", headers=auth).json()
    assert p["avg_monthly_net"] == "500.00" and p["pace"] == "behind"
