import json

import httpx
import pytest

from app.integrations.gemini import GeminiClient
from app.integrations.llm import LLMError, parse_json_object


def client_with(handler, retries=1):
    return GeminiClient("SECRET-KEY-123", "gemini-test", max_retries=retries, transport=httpx.MockTransport(handler))


def ok_body(text="hello"):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2}}


def test_success_sends_key_in_header_not_url(monkeypatch):
    seen = {}

    def handler(req: httpx.Request):
        seen.update(url=str(req.url), key=req.headers.get("x-goog-api-key"), body=json.loads(req.content))
        return httpx.Response(200, json=ok_body("hi there"))

    assert client_with(handler).generate("sys", "prompt", json_mode=True) == "hi there"
    assert "SECRET-KEY-123" not in seen["url"] and seen["key"] == "SECRET-KEY-123"
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"


def test_retries_transient_errors(monkeypatch):
    monkeypatch.setattr("app.integrations.gemini.time.sleep", lambda s: None)
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] == 1 else httpx.Response(200, json=ok_body())

    assert client_with(handler).generate("s", "p") == "hello" and calls["n"] == 2


def test_permanent_error_raises_without_leaking_key(monkeypatch):
    monkeypatch.setattr("app.integrations.gemini.time.sleep", lambda s: None)
    with pytest.raises(LLMError) as e:
        client_with(lambda r: httpx.Response(403, json={"error": "SECRET-KEY-123 invalid"})).generate("s", "p")
    assert "SECRET-KEY-123" not in str(e.value)


def test_malformed_and_empty_responses(monkeypatch):
    monkeypatch.setattr("app.integrations.gemini.time.sleep", lambda s: None)
    with pytest.raises(LLMError):
        client_with(lambda r: httpx.Response(200, json={"candidates": []})).generate("s", "p")
    with pytest.raises(LLMError):
        client_with(lambda r: httpx.Response(200, json=ok_body("   "))).generate("s", "p")


def test_network_error_becomes_llmerror(monkeypatch):
    monkeypatch.setattr("app.integrations.gemini.time.sleep", lambda s: None)

    def handler(req):
        raise httpx.ConnectError("boom")

    with pytest.raises(LLMError):
        client_with(handler).generate("s", "p")


def test_parse_json_object():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(LLMError):
        parse_json_object("[1,2]")
    with pytest.raises(LLMError):
        parse_json_object("nope")


def test_settings_guards(monkeypatch):
    from app.core.config import Settings
    with pytest.raises(ValueError):
        Settings(jwt_secret="short", environment="production")
    assert Settings(jwt_secret="x" * 40, environment="production",
                    database_url="postgres://u:p@h/db").database_url.startswith("postgresql+psycopg://")
    with pytest.raises(ValueError):
        Settings(jwt_secret="x" * 40, database_url="mysql://u:p@h/db")
    with pytest.raises(ValueError):
        Settings(jwt_secret="x" * 40, environment="production", cors_origins="*")


def test_log_redaction():
    from app.core.logging import redact
    out = redact("Authorization: Bearer abc.def.ghi password=hunter2 api_key=ZZZ")
    assert "hunter2" not in out and "ZZZ" not in out and "abc.def.ghi" not in out
