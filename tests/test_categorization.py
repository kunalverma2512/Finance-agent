from datetime import date

import pytest

from app.services.ml_classifier import MerchantClassifier
from tests.conftest import add_tx, cat_id
from tests.test_csv_import import upload

D = date.today().isoformat()


class FakeLLM:
    def __init__(self, reply: str):
        self.reply, self.calls = reply, 0

    def generate(self, system, prompt, *, json_mode=False):
        self.calls += 1
        return self.reply


def test_builtin_rules_set_source_and_confidence(client, auth, account):
    tx = add_tx(client, auth, account["id"], 12, description="Netflix.com subscription")
    assert (tx["category_name"], tx["category_source"], tx["category_confidence"]) == ("Subscriptions", "RULE", "0.900")


def test_longest_keyword_wins(client, auth, account):
    tx = add_tx(client, auth, account["id"], 12, description="Walmart Grocery pickup")
    assert tx["category_name"] == "Groceries"  # 'walmart grocery' beats 'walmart' (Shopping)


def test_user_rule_beats_builtin_keyword(client, auth, account):
    food = cat_id(client, auth, "Food")
    r = client.post("/api/v1/category-rules", json={"pattern": "netflix", "category_id": food}, headers=auth)
    assert r.status_code == 201
    tx = add_tx(client, auth, account["id"], 12, description="Netflix.com")
    assert tx["category_name"] == "Food" and tx["category_confidence"] == "1.000"


def test_user_correction_survives_recategorization_and_propagates(client, auth, account):
    a = add_tx(client, auth, account["id"], 9, description="Zorbo Market 1")
    b = add_tx(client, auth, account["id"], 8, description="Zorbo Market 2")
    groceries = cat_id(client, auth, "Groceries")
    client.patch(f"/api/v1/transactions/{a['id']}", json={"category_id": groceries, "create_rule": True}, headers=auth)
    assert client.get(f"/api/v1/transactions/{b['id']}", headers=auth).json()["category_name"] == "Groceries"
    # a later import of the same merchant is categorised by the new rule
    upload(client, auth, account, f"date,description,amount\n{D},ZORBO MARKET 77,-5\n")
    items = client.get("/api/v1/transactions?search=zorbo", headers=auth).json()["items"]
    assert len(items) == 3 and all(t["category_name"] == "Groceries" for t in items)
    client.post("/api/v1/transactions/recategorize", headers=auth)
    first = client.get(f"/api/v1/transactions/{a['id']}", headers=auth).json()
    assert first["category_source"] == "USER"


def test_user_category_cannot_be_used_by_other_user(client, auth, auth_b):
    mine = client.post("/api/v1/categories", json={"name": "Pets", "kind": "expense"}, headers=auth).json()
    assert client.get("/api/v1/categories", headers=auth_b).json() and \
        mine["id"] not in [c["id"] for c in client.get("/api/v1/categories", headers=auth_b).json()]
    r = client.post("/api/v1/category-rules", json={"pattern": "petco", "category_id": mine["id"]}, headers=auth_b)
    assert r.status_code == 404


def test_ml_classifier_learns_from_user_labels():
    ml = MerchantClassifier().fit([("fresh bakery downtown", 1)] * 12 + [("city gas station", 2)] * 12)
    assert ml.predict("fresh bakery") == (1, pytest.approx(1.0, abs=0.2))
    assert ml.predict("totally unseen words") is None
    assert MerchantClassifier().fit([("a b", 1)]).predict("a b") is None  # too little data


def test_ml_source_is_used_after_enough_labelled_history(client, auth, account):
    pets = client.post("/api/v1/categories", json={"name": "Pets", "kind": "expense"}, headers=auth).json()
    client.post("/api/v1/category-rules", json={"pattern": "furrypaws", "category_id": pets["id"]}, headers=auth)
    health = cat_id(client, auth, "Health")
    for i in range(12):
        add_tx(client, auth, account["id"], 10 + i, description="Furrypaws Vetshop")
        add_tx(client, auth, account["id"], 20 + i, description="Zenmed Wellness", category=health)
    upload(client, auth, account, f"date,description,amount\n{D},Zenmed Wellness Centre,-33\n")
    tx = client.get("/api/v1/transactions?search=wellness+centre", headers=auth).json()["items"][0]
    assert (tx["category_name"], tx["category_source"]) == ("Health", "ML")


def test_llm_fallback_only_when_requested_and_output_is_validated(client, auth, account):
    fake = FakeLLM('{"qwertyco": "Education", "other": "Not A Category"}')
    client.app.state.llm_override = fake
    csv = f"date,description,amount\n{D},Qwertyco,-10\n"
    upload(client, auth, account, csv)
    assert fake.calls == 0  # LLM is never called unless explicitly requested
    s = client.post("/api/v1/transactions/recategorize?use_llm=true", headers=auth).json()
    assert fake.calls == 1 and s["LLM"] == 1
    tx = client.get("/api/v1/transactions", headers=auth).json()["items"][0]
    assert (tx["category_name"], tx["category_source"]) == ("Education", "LLM")


def test_llm_garbage_or_invalid_category_is_ignored(client, auth, account):
    client.app.state.llm_override = FakeLLM("not json at all")
    upload(client, auth, account, f"date,description,amount\n{D},Mystery Co,-10\n")
    assert client.post("/api/v1/transactions/recategorize?use_llm=true", headers=auth).json()["LLM"] == 0
    client.app.state.llm_override = FakeLLM('{"mystery co": "Salary"}')  # income category for an expense
    assert client.post("/api/v1/transactions/recategorize?use_llm=true", headers=auth).json()["LLM"] == 0
