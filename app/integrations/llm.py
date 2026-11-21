"""LLM abstraction. Services/agents depend on this protocol, never on a vendor SDK."""
import json
import re
from typing import Protocol


class LLMError(Exception):
    """Any failure talking to the LLM (network, quota, bad output)."""


class LLMClient(Protocol):
    def generate(self, system: str, prompt: str, *, json_mode: bool = False) -> str: ...


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from model output (tolerates ```json fences)."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError("LLM returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("LLM JSON output is not an object")
    return data
