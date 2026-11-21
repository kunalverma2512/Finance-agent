from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings
from tests.conftest import register_and_login


def test_register_login_profile(client):
    h = register_and_login(client, "User@Example.com")
    p = client.get("/api/v1/profile", headers=h).json()
    assert p["email"] == "user@example.com" and "hashed_password" not in p


def test_password_is_hashed_in_db(client, db):
    register_and_login(client)
    from sqlalchemy import select
    from app.models import User
    u = db.scalar(select(User))
    assert u.hashed_password.startswith("$2") and "Passw0rdX" not in u.hashed_password


def test_duplicate_email_conflict(client):
    register_and_login(client)
    r = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "Passw0rdX"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMAIL_TAKEN"


def test_weak_password_and_bad_email_rejected_without_echoing_secret(client):
    r = client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "short"})
    assert r.status_code == 422 and "short" not in r.text
    assert client.post("/api/v1/auth/register", json={"email": "nope", "password": "Passw0rdX"}).status_code == 422
    assert client.post("/api/v1/auth/register", json={"email": "x@example.com",
                                                      "password": "onlyletters"}).status_code == 422


def test_wrong_password_and_unknown_user_same_error(client):
    register_and_login(client)
    a = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "Wrong1234"})
    b = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "Wrong1234"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_missing_and_invalid_token(client):
    r = client.get("/api/v1/profile")
    assert r.status_code == 401 and r.json()["error"]["code"] == "NOT_AUTHENTICATED"
    r = client.get("/api/v1/profile", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "INVALID_TOKEN"


def test_expired_token(client):
    h = register_and_login(client)
    s = get_settings()
    now = datetime.now(timezone.utc)
    tok = jwt.encode({"sub": "1", "tv": 0, "exp": now - timedelta(minutes=1)}, s.jwt_secret, algorithm="HS256")
    r = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_token_signed_with_wrong_key_or_alg_none(client):
    register_and_login(client)
    now = datetime.now(timezone.utc)
    forged = jwt.encode({"sub": "1", "tv": 0, "exp": now + timedelta(hours=1)}, "x" * 40, algorithm="HS256")
    assert client.get("/api/v1/profile", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    none_tok = jwt.encode({"sub": "1", "tv": 0, "exp": now + timedelta(hours=1)}, None, algorithm="none")
    assert client.get("/api/v1/profile", headers={"Authorization": f"Bearer {none_tok}"}).status_code == 401


def test_logout_invalidates_existing_tokens(client):
    h = register_and_login(client)
    assert client.post("/api/v1/auth/logout", headers=h).status_code == 200
    assert client.get("/api/v1/profile", headers=h).status_code == 401


def test_login_rate_limit(client):
    get_settings().rate_limit_enabled = True
    codes = [client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "x"}).status_code
             for _ in range(12)]
    assert codes[-1] == 429 and codes[0] == 401


def test_error_envelope_for_unknown_route_and_health(client):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404 and set(r.json()["error"]) >= {"code", "message"}
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").json()["checks"]["database"] == "ok"


def test_security_headers_and_request_id(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-request-id"]
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
