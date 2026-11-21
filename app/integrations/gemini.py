"""Gemini REST client (httpx). No vendor SDK: one endpoint, easy to mock and audit."""
import logging
import time

import httpx

from app.core.config import Settings, get_settings
from app.integrations.llm import LLMClient, LLMError

log = logging.getLogger(__name__)
_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class UsageTracker:
    """In-process token counters (exposed on /health/ready-adjacent metrics logs)."""
    calls = 0
    prompt_tokens = 0
    output_tokens = 0


class GeminiClient:
    def __init__(self, api_key: str, model: str, timeout: float = 20.0, max_retries: int = 2,
                 transport: httpx.BaseTransport | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._max_retries = max_retries
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def generate(self, system: str, prompt: str, *, json_mode: bool = False) -> str:
        body: dict = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        url = f"{_BASE}/{self._model}:generateContent"
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):
            started = time.monotonic()
            try:
                # key travels in a header, never in the URL, so it cannot leak into logs
                resp = self._client.post(url, json=body, headers={"x-goog-api-key": self._api_key})
                if resp.status_code in (429, 500, 502, 503, 504):
                    last = LLMError(f"Gemini temporary error {resp.status_code}")
                    time.sleep(min(2 ** attempt * 0.5, 4))
                    continue
                if resp.status_code != 200:
                    raise LLMError(f"Gemini request failed with status {resp.status_code}")
                data = resp.json()
                text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
                usage = data.get("usageMetadata", {})
                UsageTracker.calls += 1
                UsageTracker.prompt_tokens += int(usage.get("promptTokenCount", 0))
                UsageTracker.output_tokens += int(usage.get("candidatesTokenCount", 0))
                log.info("llm_call", extra={"model": self._model, "duration_ms":
                         int((time.monotonic() - started) * 1000), "prompt_tokens":
                         usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount")})
                if not text.strip():
                    raise LLMError("Gemini returned an empty response")
                return text
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last = LLMError(f"Gemini call failed: {type(exc).__name__}")
                time.sleep(min(2 ** attempt * 0.5, 4))
        raise last or LLMError("Gemini call failed")


def build_llm(settings: Settings | None = None) -> LLMClient | None:
    s = settings or get_settings()
    if not s.llm_enabled:
        return None
    return GeminiClient(s.gemini_api_key, s.gemini_model, s.gemini_timeout_seconds)
