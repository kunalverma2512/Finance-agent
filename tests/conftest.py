"""Test harness: REAL PostgreSQL (TEST_DATABASE_URL), schema built by running the Alembic migrations."""
import os

os.environ.setdefault("TEST_DATABASE_URL", "postgresql+psycopg://fin:fin@localhost:5432/finance_test")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-32"
os.environ["ENVIRONMENT"] = "test"
os.environ["MONITOR_INTERVAL_MINUTES"] = "0"
os.environ["GEMINI_API_KEY"] = ""
os.environ["LOG_JSON"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"

from datetime import date  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.db.session import get_engine, get_sessionmaker  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.category_data import ensure_system_categories  # noqa: E402

CLEAN_ORDER = ["alerts", "insights", "chat_messages", "agent_runs", "audit_logs", "budget_items", "budgets",
               "financial_goals", "transactions", "category_rules", "accounts"]


@pytest.fixture(scope="session", autouse=True)
def _schema():
    try:
        with get_engine().connect() as conn:
            pass
    except Exception:
        yield
        return
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")  # proves migrations work from scratch
    yield


@pytest.fixture(autouse=True)
def _clean():
    limiter.reset()
    get_settings().rate_limit_enabled = False
    yield
    try:
        with get_engine().begin() as conn:
            for t in CLEAN_ORDER:
                conn.execute(text(f"DELETE FROM {t}"))
            conn.execute(text("DELETE FROM categories WHERE user_id IS NOT NULL"))
            conn.execute(text("DELETE FROM users"))
    except Exception:
        pass


@pytest.fixture
def db():
    with get_sessionmaker()() as session:
        ensure_system_categories(session)
        yield session


@pytest.fixture
def client(db):
    app = create_app()
    app.state.llm_override = None
    with TestClient(app) as c:
        yield c


def register_and_login(client: TestClient, email="a@example.com", password="Passw0rdX", currency="USD") -> dict:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "currency": currency})
    assert r.status_code == 201, r.text
    t = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture
def auth(client):
    return register_and_login(client)


@pytest.fixture
def auth_b(client):
    return register_and_login(client, "b@example.com")


@pytest.fixture
def account(client, auth):
    r = client.post("/api/v1/accounts", json={"name": "Main", "type": "checking"}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def cat_id(client, headers, name: str) -> int:
    cats = client.get("/api/v1/categories", headers=headers).json()
    return next(c["id"] for c in cats if c["name"] == name)


def add_tx(client, headers, account_id, amount, direction="expense", description="Test purchase",
           on: date | None = None, category: int | None = None) -> dict:
    body = {"account_id": account_id, "posted_on": (on or date.today()).isoformat(), "amount": str(amount),
            "direction": direction, "description": description}
    if category:
        body["category_id"] = category
    r = client.post("/api/v1/transactions", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
