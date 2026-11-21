"""Sliding-window rate limiter (in-process).

Limitation: state is per process. Behind several instances use a shared store
(e.g. Redis); the interface below is intentionally tiny so it can be swapped.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimitedError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                raise RateLimitedError("Too many requests, please slow down")
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def auth_rate_limit(request: Request) -> None:
    s = get_settings()
    if s.rate_limit_enabled:
        limiter.check(f"auth:{client_ip(request)}", s.auth_rate_limit_per_minute)


def chat_rate_limit(user_id: int) -> None:
    s = get_settings()
    if s.rate_limit_enabled:
        limiter.check(f"chat:{user_id}", s.chat_rate_limit_per_minute)
