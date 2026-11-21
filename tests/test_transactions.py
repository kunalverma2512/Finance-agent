from datetime import date, timedelta

from tests.conftest import add_tx, cat_id


def test_create_list_filter_paginate(client, auth, account):
    for i in range(5):
        add_tx(client, auth, account["id"], 10 + i, description=f"Starbucks {i}",
               on=date.today() - timedelta(days=i))
    add_tx(client, auth, account["id"], 1000, "income", "Payroll")
    r = client.get("/api/v1/transactions?limit=2&offset=0", headers=auth).json()
    assert r["total"] == 6 and len(r["items"]) == 2
    r = client.get("/api/v1/transactions?direction=income", headers=auth).json()
    assert r["total"] == 1 and r["items"][0]["category_name"] == "Salary"
    r = client.get("/api/v1/transactions?search=starbucks", headers=auth).json()
    assert r["total"] == 5 and all(t["category_name"] == "Food" for t in r["items"])


def test_account_balance_is_computed(client, auth):
    acc = client.post("/api/v1/accounts", json={"name": "Bank", "opening_balance": "100.00"}, headers=auth).json()
    add_tx(client, auth, acc["id"], 40, "expense", "Pizza")
    add_tx(client, auth, acc["id"], 25.5, "income", "Refund shop")
    accounts = client.get("/api/v1/accounts", headers=auth).json()
    assert accounts[0]["balance"] == "85.50"


def test_invalid_inputs_rejected(client, auth, account):
    base = {"account_id": account["id"], "posted_on": "2026-01-01", "direction": "expense", "description": "x"}
    for bad in ({"amount": "-5"}, {"amount": "0"}, {"amount": "abc"}, {"amount": "1.234"},
                {"amount": "5", "direction": "sideways"}, {"amount": "5", "description": "  "},
                {"amount": "5", "posted_on": "2026-02-30"}):
        r = client.post("/api/v1/transactions", json={**base, **bad}, headers=auth)
        assert r.status_code == 422, bad


def test_unknown_account_and_transaction_ids(client, auth):
    r = client.post("/api/v1/transactions", json={"account_id": 99999, "posted_on": "2026-01-01",
                                                  "amount": "5", "direction": "expense", "description": "x"},
                    headers=auth)
    assert r.status_code == 404 and r.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"
    r = client.get("/api/v1/transactions/424242", headers=auth)
    assert r.status_code == 404 and r.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"
    assert client.get("/api/v1/transactions/abc", headers=auth).status_code == 422


def test_sql_injection_attempts_are_inert(client, auth, account):
    add_tx(client, auth, account["id"], 12, description="Coffee")
    for payload in ("'; DROP TABLE transactions; --", "' OR '1'='1", "%", "_"):
        r = client.get("/api/v1/transactions", params={"search": payload}, headers=auth)
        assert r.status_code == 200 and r.json()["total"] == 0, payload  # %, _ are escaped, not wildcards
    assert client.get("/api/v1/transactions", headers=auth).json()["total"] == 1


def test_update_and_delete(client, auth, account):
    tx = add_tx(client, auth, account["id"], 20, description="Mystery store")
    assert tx["category_id"] is None
    shopping = cat_id(client, auth, "Shopping")
    r = client.patch(f"/api/v1/transactions/{tx['id']}", json={"category_id": shopping}, headers=auth).json()
    assert r["category_name"] == "Shopping" and r["category_source"] == "USER" and r["category_confidence"] == "1.000"
    assert client.delete(f"/api/v1/transactions/{tx['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/v1/transactions/{tx['id']}", headers=auth).status_code == 404


def test_category_kind_mismatch_rejected(client, auth, account):
    tx = add_tx(client, auth, account["id"], 20, "expense", "Thing")
    r = client.patch(f"/api/v1/transactions/{tx['id']}", json={"category_id": cat_id(client, auth, "Salary")},
                     headers=auth)
    assert r.status_code == 422 and r.json()["error"]["code"] == "CATEGORY_KIND_MISMATCH"


def test_duplicate_account_name_conflict(client, auth, account):
    r = client.post("/api/v1/accounts", json={"name": "main"}, headers=auth)
    assert r.status_code == 409
