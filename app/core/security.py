"""Password hashing and JWT helpers."""
import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import UnauthorizedError


def _prehash(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes; pre-hashing removes the limit safely.
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), hashed.encode("ascii"))
    except ValueError:
        return False


def create_access_token(user_id: int, token_version: int) -> tuple[str, int]:
    s = get_settings()
    expires = timedelta(minutes=s.access_token_expire_minutes)
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "tv": token_version, "iat": now, "exp": now + expires,
               "jti": uuid.uuid4().hex}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), int(expires.total_seconds())


def decode_access_token(token: str) -> dict:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm],
                             options={"require": ["exp", "sub", "tv"]})
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired", code="TOKEN_EXPIRED") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid authentication token", code="INVALID_TOKEN") from exc
    return payload
